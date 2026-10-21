# -*- coding: utf-8 -*-
"""
SANTE DZ — SCRAPER NATIONAL GOOGLE MAPS
=======================================
Scrape les fiches publiques visibles dans Google Maps via navigateur Playwright,
sans Google Places API et donc sans clé API.

IMPORTANT :
- Ce script récupère uniquement les informations rendues publiquement visibles.
- Google peut modifier son interface ou limiter l'automatisation : le script
  contient des sélecteurs de secours et sauvegarde les données progressivement.
- Utilisez-le de manière raisonnable et respectez les conditions d'utilisation
  et les lois applicables.

Sorties :
  exports/SANTE_DZ_GOOGLE_MAPS_NATIONAL.xlsx
  exports/SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv
  exports/checkpoint.csv

Colonnes principales :
  wilaya, commune, categorie, nom, adresse, telephone, site_web,
  note, nombre_avis, latitude, longitude, google_maps_url,
  horaires, type_google, place_id_si_visible, scrape_date

Lancement :
  python scraper.py

Options :
  python scraper.py --wilaya Mostaganem
  python scraper.py --wilaya "Oran" --max-results 200
  python scraper.py --all
  python scraper.py --all --resume   (reprise automatique après interruption)
"""

import argparse
import asyncio
import csv
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from urllib.parse import quote

# Force UTF-8 encoding for console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import pandas as pd
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("DEPENDANCES MANQUANTES.")
    print("Lancez : python -m pip install -r requirements.txt")
    sys.exit(1)

BASE = Path(__file__).resolve().parent
EXPORTS = Path(r"D:\SANTE_DZ_EXPORTS")
EXPORTS.mkdir(exist_ok=True)

OUT_XLSX = EXPORTS / "SANTE_DZ_GOOGLE_MAPS_NATIONAL.xlsx"
OUT_CSV = EXPORTS / "SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv"
CHECKPOINT = EXPORTS / "checkpoint.csv"
PROGRESS = EXPORTS / "progression.json"

# En septembre 2026, le découpage est en transition vers 69 wilayas.
# Les 11 nouvelles wilayas doivent exercer pleinement leurs prérogatives
# à partir du 1er janvier 2027. On inclut néanmoins les 69 noms pour permettre
# une couverture nationale dès maintenant.
WILAYAS = [
    "Adrar", "Chlef", "Laghouat", "Oum El Bouaghi", "Batna", "Béjaïa",
    "Biskra", "Béchar", "Blida", "Bouira", "Tamanrasset", "Tébessa",
    "Tlemcen", "Tiaret", "Tizi Ouzou", "Alger", "Djelfa", "Jijel",
    "Sétif", "Saïda", "Skikda", "Sidi Bel Abbès", "Annaba", "Guelma",
    "Constantine", "Médéa", "Mostaganem", "M'Sila", "Mascara", "Ouargla",
    "Oran", "El Bayadh", "Illizi", "Bordj Bou Arréridj", "Boumerdès",
    "El Tarf", "Tindouf", "Tissemsilt", "El Oued", "Khenchela",
    "Souk Ahras", "Tipaza", "Mila", "Aïn Defla", "Naâma", "Aïn Témouchent",
    "Ghardaïa", "Relizane", "Timimoun", "Bordj Badji Mokhtar",
    "Ouled Djellal", "Béni Abbès", "In Salah", "In Guezzam",
    "Touggourt", "Djanet", "El M'Ghair", "El Meniaa",
    # nouvelles wilayas prévues par le nouveau découpage
    "Aflou", "Barika", "El Kantara", "Bir El Ater", "El Aricha",
    "Ksar Chellala", "Aïn Oussara", "Messaad", "Ksar El Boukhari",
    "Bou Saâda", "El Bayadh Sidi Cheikh",
]

# Requêtes volontairement larges : on cherche des catégories de santé
# susceptibles d'apparaître comme fiches Google Maps.
CATEGORIES = [
    "médecin",
    "cabinet médical",
    "médecin généraliste",
    "médecin spécialiste",
    "dentiste",
    "cabinet dentaire",
    "pharmacie",
    "laboratoire médical",
    "clinique",
    "hôpital",
    "polyclinique",
    "centre médical",
    "centre de santé",
    "radiologue",
    "centre de radiologie",
    "kinésithérapeute",
    "kinésithérapie",
    "sage-femme",
    "ophtalmologue",
    "pédiatre",
    "gynécologue",
    "cardiologue",
    "dermatologue",
    "ORL",
    "neurologue",
    "urologue",
    "gastro-entérologue",
    "psychologue",
    "psychiatre",
    "nutritionniste",
    "orthophoniste",
    "ostéopathe",
    "vétérinaire",
    "centre d'imagerie médicale",
]

FIELDS = [
    "wilaya", "commune", "categorie_recherche", "nom", "adresse",
    "telephone", "site_web", "note", "nombre_avis", "horaires",
    "latitude", "longitude", "google_maps_url", "place_id_si_visible",
    "type_google", "statut", "scrape_date", "source"
]


class ScrapeErrorType(Enum):
    """Classification des types d'erreurs pour décider du retry."""
    NONE = "none"                    # Aucun résultat (normal, marquer comme terminé)
    PAGE_NOT_LOADED = "page_not_loaded"
    TIMEOUT = "timeout"
    DOM_CHANGED = "dom_changed"
    RATE_LIMITED = "rate_limited"
    CAPTCHA = "captcha"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class ScrapeError(Exception):
    """Exception avec classification d'erreur pour la logique de retry."""
    def __init__(self, message: str, error_type: ScrapeErrorType = ScrapeErrorType.UNKNOWN, recoverable: bool = True):
        super().__init__(message)
        self.error_type = error_type
        self.recoverable = recoverable


def clean(s):
    if s is None:
        return ""
    s = str(s).replace("\u200b", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_float(value):
    if value is None:
        return None
    m = re.search(r"(-?\d+(?:[.,]\d+)?)", str(value))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except Exception:
        return None


def extract_lat_lng(url):
    if not url:
        return None, None
    patterns = [
        r"@(-?\d+\.\d+),(-?\d+\.\d+)",
        r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)",
        r"ll=(-?\d+\.\d+),(-?\d+\.\d+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return float(m.group(1)), float(m.group(2))
    return None, None


def stable_key(row):
    raw = "|".join([
        clean(row.get("nom")),
        clean(row.get("adresse")),
        clean(row.get("telephone")),
        str(row.get("latitude") or ""),
        str(row.get("longitude") or ""),
    ]).lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def atomic_write_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_progress():
    if not PROGRESS.exists():
        return {"version": 1, "completed": [], "current": None, "updated_at": None}
    try:
        data = json.loads(PROGRESS.read_text(encoding="utf-8"))
        data.setdefault("version", 1)
        data.setdefault("completed", [])
        data.setdefault("current", None)
        return data
    except Exception:
        return {"version": 1, "completed": [], "current": None, "updated_at": None}


def save_progress(completed, current=None):
    # Dédouble et trie par ordre WILAYAS puis CATEGORIES
    seen = set()
    unique = []
    for x in completed:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            t = tuple(x)
            if t not in seen:
                seen.add(t)
                unique.append(list(t))
    unique.sort(key=lambda x: (
        WILAYAS.index(x[0]) if x[0] in WILAYAS else 999,
        CATEGORIES.index(x[1]) if x[1] in CATEGORIES else 999
    ))
    data = {
        "version": 1,
        "completed": unique,
        "current": current,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    atomic_write_json(PROGRESS, data)


def progress_key(wilaya, category):
    return [wilaya, category]


def bootstrap_progress(all_rows, progress):
    """If an old checkpoint exists without progression.json, infer only the
    clearly completed leading wilayas. This protects the existing national run
    while avoiding a blind restart from Adrar."""
    completed = {tuple(x) for x in progress.get("completed", []) if isinstance(x, list) and len(x) == 2}
    if completed or progress.get("current"):
        return completed
    present = {clean(r.get("wilaya")) for r in all_rows if clean(r.get("wilaya"))}
    for w in WILAYAS:
        if w in present:
            for c in CATEGORIES:
                completed.add((w, c))
        else:
            break
    save_progress([list(x) for x in completed], None)
    return completed


def load_checkpoint():
    if not CHECKPOINT.exists():
        return []
    try:
        return pd.read_csv(CHECKPOINT, dtype=str).fillna("").to_dict("records")
    except Exception:
        return []


def save_checkpoint(rows):
    if not rows:
        return
    df = pd.DataFrame(rows)
    for c in FIELDS:
        if c not in df.columns:
            df[c] = ""
    df = df[FIELDS]
    tmp = CHECKPOINT.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(CHECKPOINT)


def merge_rows(rows):
    existing = load_checkpoint()
    all_rows = existing + rows
    unique = {}
    for r in all_rows:
        unique[stable_key(r)] = r
    result = list(unique.values())
    result.sort(key=lambda x: (
        clean(x.get("wilaya")).lower(),
        clean(x.get("categorie_recherche")).lower(),
        clean(x.get("nom")).lower()
    ))
    save_checkpoint(result)
    return result


def log_info(wilaya, category, attempt, status, msg=""):
    """Log formaté : wilaya / catégorie / tentative / statut"""
    prefix = f"[{wilaya}] [{category}] [tentative {attempt}] [{status}]"
    if msg:
        print(f"    {prefix} {msg}")
    else:
        print(f"    {prefix}")


async def text_of(locator):
    try:
        if await locator.count():
            return clean(await locator.first.inner_text())
    except Exception:
        pass
    return ""


async def attr_of(locator, attr):
    try:
        if await locator.count():
            return clean(await locator.first.get_attribute(attr))
    except Exception:
        pass
    return ""


async def parse_card(card, wilaya, category):
    # Les sélecteurs Google Maps évoluent. On récupère d'abord le lien,
    # puis les textes disponibles dans la carte.
    row = {
        "wilaya": wilaya,
        "commune": "",
        "categorie_recherche": category,
        "nom": "",
        "adresse": "",
        "telephone": "",
        "site_web": "",
        "note": "",
        "nombre_avis": "",
        "horaires": "",
        "latitude": None,
        "longitude": None,
        "google_maps_url": "",
        "place_id_si_visible": "",
        "type_google": "",
        "statut": "visible",
        "scrape_date": datetime.now().isoformat(timespec="seconds"),
        "source": "Google Maps public UI",
    }

    try:
        link = card.locator("a.hfpxzc").first
        if await link.count():
            row["google_maps_url"] = await link.get_attribute("href") or ""
    except Exception:
        pass

    row["nom"] = await attr_of(card.locator("div.qBF1Pd"), "aria-label")
    if not row["nom"]:
        row["nom"] = await text_of(card.locator("div.qBF1Pd"))

    # Fallback : aria-label du lien principal
    if not row["nom"]:
        row["nom"] = await attr_of(card.locator("a.hfpxzc"), "aria-label")

    txt = await text_of(card)
    lines = [clean(x) for x in txt.splitlines() if clean(x)]

    # Extraction de la note et du nombre d'avis
    for line in lines:
        m = re.search(r"\b([0-5](?:[.,]\d)?)\b", line)
        if m and not row["note"]:
            row["note"] = m.group(1).replace(",", ".")
        m = re.search(r"\(?\s*([\d .]+)\s*(?:avis|reviews?)\s*\)?", line, re.I)
        if m:
            row["nombre_avis"] = re.sub(r"\D", "", m.group(1))

    # Téléphone
    phone_re = re.compile(r"(?:\+213|0)(?:[\s.-]?\d){8,10}")
    for line in lines:
        m = phone_re.search(line)
        if m:
            row["telephone"] = clean(m.group(0))
            break

    # Adresse : heuristique ; la fiche détaillée sera ouverte ensuite
    if len(lines) >= 2:
        candidates = [x for x in lines[1:] if not phone_re.search(x)]
        if candidates:
            row["adresse"] = candidates[0]

    row["latitude"], row["longitude"] = extract_lat_lng(row["google_maps_url"])
    return row


async def extract_detail(page, row):
    """Ouvre la fiche et récupère les informations visibles supplémentaires."""
    url = row.get("google_maps_url") or ""
    if not url:
        return row

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1200)

        # URL finale : contient souvent les coordonnées
        final_url = page.url
        row["google_maps_url"] = final_url
        lat, lng = extract_lat_lng(final_url)
        if lat is not None:
            row["latitude"], row["longitude"] = lat, lng

        # Nom
        title = await text_of(page.locator("h1"))
        if title:
            row["nom"] = title

        # Récupération des boutons/liens visibles
        buttons = page.locator("button")
        n = min(await buttons.count(), 120)
        texts = []
        for i in range(n):
            try:
                t = clean(await buttons.nth(i).get_attribute("aria-label"))
                if t:
                    texts.append(t)
            except Exception:
                pass

        # Adresse
        for t in texts:
            if any(k in t.lower() for k in ["adresse", "address", "itinéraire", "directions"]):
                if row["adresse"] == "":
                    row["adresse"] = t
                break

        # Téléphone
        phone_re = re.compile(r"(?:\+213|0)(?:[\s.-]?\d){8,10}")
        for t in texts:
            m = phone_re.search(t)
            if m:
                row["telephone"] = clean(m.group(0))
                break

        # Liens
        links = page.locator("a")
        n = min(await links.count(), 150)
        for i in range(n):
            try:
                href = await links.nth(i).get_attribute("href")
                txt = clean(await links.nth(i).inner_text())
                if href and href.startswith("http") and "google." not in href:
                    if row["site_web"] == "":
                        row["site_web"] = href
                if phone_re.search(txt):
                    row["telephone"] = phone_re.search(txt).group(0)
            except Exception:
                pass

        # Corps de page : utile pour horaires et informations supplémentaires
        body = await text_of(page.locator("body"))
        if body:
            m = phone_re.search(body)
            if m and not row["telephone"]:
                row["telephone"] = m.group(0)

            # Avis / note
            if not row["note"]:
                m = re.search(r"\b([0-5](?:[.,]\d)?)\b", body)
                if m:
                    row["note"] = m.group(1).replace(",", ".")

        # Google place id : peut apparaître dans certaines URLs/HTML.
        html = await page.content()
        m = re.search(r"ChIJ[A-Za-z0-9_-]{10,}", html)
        if m:
            row["place_id_si_visible"] = m.group(0)

    except PlaywrightTimeoutError:
        row["statut"] = "timeout"
        raise ScrapeError("Timeout lors de l'ouverture de la fiche", ScrapeErrorType.TIMEOUT)
    except Exception as e:
        row["statut"] = "erreur: " + clean(str(e))[:180]
        raise ScrapeError(f"Erreur extraction détail: {e}", ScrapeErrorType.UNKNOWN)

    return row


def classify_error(error_msg: str, exception: Exception = None) -> ScrapeErrorType:
    """Classifie le type d'erreur pour décider de la stratégie de retry."""
    msg = (error_msg or "").lower()
    exc_type = type(exception).__name__ if exception else ""
    
    # CAPTCHA / blocage anti-bot
    if any(k in msg for k in ["captcha", "recaptcha", "hcaptcha", "verify you are human", "unusual traffic", "automated queries", "blocked", "sorry"]):
        return ScrapeErrorType.CAPTCHA
    
    # Rate limiting
    if any(k in msg for k in ["rate limit", "too many requests", "429", "quota exceeded", "request limit"]):
        return ScrapeErrorType.RATE_LIMITED
    
    # Timeout
    if any(k in msg for k in ["timeout", "timed out", "PlaywrightTimeoutError"]):
        return ScrapeErrorType.TIMEOUT
    
    # DOM modifié / sélecteurs invalides
    if any(k in msg for k in ["no such element", "element not found", "selector", "panneau de résultats", "result panel", "feed"]):
        return ScrapeErrorType.DOM_CHANGED
    
    # Page non chargée
    if any(k in msg for k in ["navigation", "page load", "net::", "connection", "dns", "network", "ERR_", "socket"]):
        return ScrapeErrorType.NETWORK_ERROR
    
    return ScrapeErrorType.UNKNOWN


async def search_category_with_retry(page, wilaya, category, max_results, max_retries=3, base_delay=2.0):
    """
    Recherche une catégorie avec retry et backoff exponentiel.
    Retourne (rows, error_type) où rows est None si échec définitif.
    """
    query = f"{category} {wilaya} Algérie"
    url = "https://www.google.com/maps/search/" + quote(query) + "?hl=fr"
    
    last_error = None
    last_error_type = ScrapeErrorType.UNKNOWN
    
    for attempt in range(1, max_retries + 1):
        log_info(wilaya, category, attempt, "DEBUT")
        
        try:
            # Navigation vers la page de recherche
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(1800)
            except PlaywrightTimeoutError:
                last_error = "Timeout navigation"
                last_error_type = ScrapeErrorType.TIMEOUT
                log_info(wilaya, category, attempt, "TIMEOUT_NAV", last_error)
                if attempt < max_retries:
                    await asyncio.sleep(base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1))
                    continue
                return None, last_error_type
            except Exception as e:
                last_error = f"Erreur navigation: {e}"
                last_error_type = classify_error(str(e), e)
                log_info(wilaya, category, attempt, "ERREUR_NAV", f"{last_error_type.value}: {last_error}")
                if attempt < max_retries and last_error_type != ScrapeErrorType.CAPTCHA:
                    await asyncio.sleep(base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1))
                    continue
                return None, last_error_type

            # Recherche du panneau de résultats
            panel = page.locator('div[role="feed"]').first
            if not await panel.count():
                # Vérifier si c'est un CAPTCHA ou blocage
                page_content = await page.content()
                if any(k in page_content.lower() for k in ["captcha", "recaptcha", "unusual traffic", "verify you are human", "automated queries"]):
                    last_error = "CAPTCHA détecté"
                    last_error_type = ScrapeErrorType.CAPTCHA
                elif "rate limit" in page_content.lower() or "too many requests" in page_content.lower():
                    last_error = "Rate limiting détecté"
                    last_error_type = ScrapeErrorType.RATE_LIMITED
                else:
                    last_error = "Panneau de résultats introuvable (DOM modifié ou page vide)"
                    last_error_type = ScrapeErrorType.DOM_CHANGED
                
                log_info(wilaya, category, attempt, "PANEL_MISSING", f"{last_error_type.value}: {last_error}")
                
                if attempt < max_retries and last_error_type in (ScrapeErrorType.DOM_CHANGED, ScrapeErrorType.NETWORK_ERROR, ScrapeErrorType.TIMEOUT):
                    await asyncio.sleep(base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1))
                    continue
                return None, last_error_type

            # Scroll du panneau des résultats
            seen_urls = set()
            raw_rows = []
            
            for scroll_no in range(35):
                cards = panel.locator('div[role="article"]')
                count = await cards.count()

                for i in range(count):
                    try:
                        card = cards.nth(i)
                        r = await parse_card(card, wilaya, category)
                        if r["nom"] or r["google_maps_url"]:
                            key = r["google_maps_url"] or r["nom"]
                            if key not in seen_urls:
                                seen_urls.add(key)
                                raw_rows.append(r)
                                if len(raw_rows) >= max_results:
                                    break
                    except Exception:
                        continue

                if len(raw_rows) >= max_results:
                    break

                try:
                    await panel.evaluate("(el) => el.scrollTo(0, el.scrollHeight)")
                except Exception:
                    break
                await page.wait_for_timeout(900)

            # Si aucun résultat trouvé (cas normal, pas d'erreur)
            if not raw_rows:
                log_info(wilaya, category, attempt, "ZERO_RESULT", "Aucun résultat trouvé")
                return [], ScrapeErrorType.NONE

            # Ouvre les fiches individuellement pour enrichir GPS/téléphone/site/etc.
            enriched = []
            for idx, r in enumerate(raw_rows, 1):
                log_info(wilaya, category, attempt, "FICHE", f"{idx}/{len(raw_rows)} : {r.get('nom','')[:55]}")
                try:
                    r = await extract_detail(page, r)
                    enriched.append(r)
                except ScrapeError as e:
                    # Si erreur sur une fiche individuelle, on garde la version de base
                    log_info(wilaya, category, attempt, "FICHE_ERREUR", f"{e.error_type.value}: {e}")
                    enriched.append(r)
                except Exception as e:
                    log_info(wilaya, category, attempt, "FICHE_ERREUR", f"UNKNOWN: {e}")
                    enriched.append(r)

                # retour à la recherche pour la prochaine fiche
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(700)
                except Exception as e:
                    log_info(wilaya, category, attempt, "RETOUR_ERREUR", f"Impossible de retourner à la recherche: {e}")
                    # On continue avec les fiches restantes

            log_info(wilaya, category, attempt, "OK", f"+{len(enriched)} résultats")
            return enriched, ScrapeErrorType.NONE

        except ScrapeError as e:
            last_error = str(e)
            last_error_type = e.error_type
            log_info(wilaya, category, attempt, "SCRAPE_ERROR", f"{e.error_type.value}: {last_error}")
            if attempt < max_retries and e.recoverable:
                wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                if e.error_type == ScrapeErrorType.RATE_LIMITED:
                    wait = max(wait, 30)  # Attente plus longue pour rate limit
                elif e.error_type == ScrapeErrorType.CAPTCHA:
                    wait = max(wait, 120)  # Attente très longue pour CAPTCHA
                log_info(wilaya, category, attempt, "RETRY_WAIT", f"Attente {wait:.1f}s avant retry")
                await asyncio.sleep(wait)
                continue
            return None, last_error_type
        
        except Exception as e:
            last_error = f"Erreur inattendue: {e}"
            last_error_type = classify_error(str(e), e)
            log_info(wilaya, category, attempt, "EXCEPTION", f"{last_error_type.value}: {last_error}")
            if attempt < max_retries and last_error_type in (ScrapeErrorType.TIMEOUT, ScrapeErrorType.NETWORK_ERROR, ScrapeErrorType.DOM_CHANGED):
                wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                log_info(wilaya, category, attempt, "RETRY_WAIT", f"Attente {wait:.1f}s avant retry")
                await asyncio.sleep(wait)
                continue
            return None, last_error_type

    # Tous les retries échoués
    log_info(wilaya, category, max_retries, "ECHEC_DEFINITIF", f"Type: {last_error_type.value}, Erreur: {last_error}")
    return None, last_error_type


async def run(args):
    all_rows = load_checkpoint()
    progress = load_progress()
    completed = bootstrap_progress(all_rows, progress)

    start_time = time.time()
    last_new_count = len(all_rows)
    last_new_time = start_time
    last_checkpoint_time = start_time
    total_queries = 0
    total_results = 0
    total_new = 0
    total_duplicates = 0

    def print_live_dashboard(wilaya, commune, category, query, results_found, new_unique, duplicates):
        nonlocal last_new_count, last_new_time, total_queries, total_results, total_new, total_duplicates
        total_queries += 1
        total_results += results_found
        total_new += new_unique
        total_duplicates += duplicates
        now = time.time()
        elapsed = now - start_time
        mins = elapsed / 60.0
        fpm = (len(all_rows) / mins) if mins > 0 else 0.0
        qpm = (total_queries / mins) if mins > 0 else 0.0
        nfpm = (total_new / mins) if mins > 0 else 0.0
        last_save = now - last_checkpoint_time
        since_new = now - last_new_time if total_new > 0 else 0.0
        if new_unique > 0:
            last_new_time = now
            last_new_count = len(all_rows)

        gps = sum(1 for r in all_rows if str(r.get("latitude", "")).strip() and str(r.get("longitude", "")).strip())
        phones = sum(1 for r in all_rows if str(r.get("telephone", "")).strip())
        pids = sum(1 for r in all_rows if str(r.get("place_id_si_visible", "")).strip())
        addresses = sum(1 for r in all_rows if str(r.get("adresse", "")).strip())
        websites = sum(1 for r in all_rows if str(r.get("site_web", "")).strip())

        print()
        print("=" * 70)
        print("             🟢 MEDIZY — GOOGLE MAPS LIVE SCRAPER")
        print("=" * 70)
        print(f"📍 Wilaya       : {wilaya}")
        print(f"🏘️  Commune      : {commune}")
        print(f"🏥 Catégorie    : {category}")
        print(f"🔎 Recherche    : {query}")
        print("-" * 70)
        print("📊 RÉSULTATS")
        print(f"   Google Maps  : {results_found}")
        print(f"   Nouvelles    : {new_unique}")
        print(f"   Doublons     : {duplicates}")
        print("-" * 70)
        print("📚 BASE MEDIZY")
        print(f"   Fiches uniques : {len(all_rows)}")
        print(f"   GPS            : {gps}")
        print(f"   Téléphones     : {phones}")
        print(f"   Place ID       : {pids}")
        print(f"   Adresses       : {addresses}")
        print(f"   Sites web      : {websites}")
        print("-" * 70)
        print("🚀 PERFORMANCE")
        if new_unique > 0:
            print(f"   +{new_unique} fiches | +{sum(1 for r in all_rows[-new_unique:] if str(r.get('latitude','')).strip() and str(r.get('longitude','')).strip())} GPS | +{sum(1 for r in all_rows[-new_unique:] if str(r.get('telephone','')).strip())} téléphones | +{sum(1 for r in all_rows[-new_unique:] if str(r.get('place_id_si_visible','')).strip())} Place ID")
        else:
            print("   Aucune nouvelle fiche")
        print(f"   Fiches/min  : {fpm:.1f}")
        print(f"   Nouvelles/min : {nfpm:.1f}")
        print(f"   Requêtes/min  : {qpm:.1f}")
        print(f"   Requêtes      : {total_queries}")
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        print(f"   Temps         : {elapsed_str}")
        print(f"   Dernière sauvegarde : {int(last_save)}s")
        print(f"   Dernière nouvelle   : {int(since_new)}s")
        print("=" * 70)

    print("=" * 80)
    print("             🟢 MEDIZY — GOOGLE MAPS LIVE SCRAPER")
    print("=" * 80)
    print(f"Wilayas ciblées : {len(WILAYAS)}")
    print(f"Catégories      : {len(CATEGORIES)}")
    print(f"Checkpoint      : {len(all_rows)} lignes déjà sauvegardées")
    print(f"Progression     : {PROGRESS}")
    print(f"Retry config    : max {args.max_retries} tentatives, délai base {args.base_delay}s (exponentiel)")
    print()

    targets = WILAYAS if args.all else [args.wilaya]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not args.visible,
            slow_mo=50 if args.visible else 0,
        )
        context = await browser.new_context(
            locale="fr-FR",
            timezone_id="Africa/Algiers",
            viewport={"width": 1440, "height": 1000},
        )
        page = await context.new_page()

        try:
            for wi, wilaya in enumerate(targets, 1):
                print()
                print("#" * 80)
                print(f"WILAYA {wi}/{len(targets)} : {wilaya}")
                print("#" * 80)

                for ci, category in enumerate(CATEGORIES, 1):
                    key = (wilaya, category)
                    if args.resume and key in completed:
                        log_info(wilaya, category, 0, "SKIP", "déjà terminée")
                        continue

                    current = [wilaya, category]
                    save_progress([list(x) for x in completed], current)
                    log_info(wilaya, category, 1, "REPRISE")

                    rows, error_type = await search_category_with_retry(
                        page, wilaya, category, args.max_results,
                        max_retries=args.max_retries,
                        base_delay=args.base_delay
                    )

                    new_unique = 0
                    duplicates = 0
                    if rows is None:
                        log_info(wilaya, category, args.max_retries, "NON_VALIDEE", 
                                f"Échec technique ({error_type.value}) — reprise au prochain lancement")
                        save_progress([list(x) for x in completed], current)
                        print_live_dashboard(wilaya, "", category, f"{category} {wilaya} Algérie", 0, 0, 0)
                        continue

                    # Calculer les nouvelles fiches et doublons
                    seen_keys = {r.get("google_maps_url", "") or r.get("nom", "") for r in all_rows}
                    new_rows = []
                    for r in rows:
                        key = r.get("google_maps_url", "") or r.get("nom", "")
                        if key in seen_keys:
                            duplicates += 1
                        else:
                            seen_keys.add(key)
                            new_rows.append(r)
                    new_unique = len(new_rows)

                    if new_rows:
                        all_rows = merge_rows(new_rows)
                        log_info(wilaya, category, 1, "MERGE_OK", f"TOTAL UNIQUE = {len(all_rows)}")
                    else:
                        log_info(wilaya, category, 1, "ZERO_RESULT", "Aucun résultat (normal)")

                    completed.add(key)
                    save_checkpoint(all_rows)
                    last_checkpoint_time = time.time()
                    save_progress([list(x) for x in completed], None)
                    log_info(wilaya, category, 1, "VALIDEE", "Progression sauvegardée")

                    query = f"{category} {wilaya} Algérie"
                    print_live_dashboard(wilaya, "", category, query, len(rows) if rows else 0, new_unique, duplicates)

                    await asyncio.sleep(args.delay)

        except KeyboardInterrupt:
            save_checkpoint(all_rows)
            save_progress([list(x) for x in completed], progress.get("current"))
            print("\nArrêt demandé. Données et progression conservées.")
            raise
        finally:
            await context.close()
            await browser.close()

    # Export final
    all_rows = load_checkpoint()
    df = pd.DataFrame(all_rows)

    for c in FIELDS:
        if c not in df.columns:
            df[c] = ""
    df = df[FIELDS].drop_duplicates(subset=["nom", "adresse", "telephone", "latitude", "longitude"])
    df = df.sort_values(["wilaya", "commune", "categorie_recherche", "nom"], na_position="last")

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Google Maps")
        df[df["latitude"].notna() & df["longitude"].notna()].to_excel(writer, index=False, sheet_name="GPS présents")
        df[df["telephone"].astype(str).str.strip().ne("")].to_excel(writer, index=False, sheet_name="Téléphones")
        df[df["telephone"].astype(str).str.strip().eq("")].to_excel(writer, index=False, sheet_name="Téléphones manquants")
        stats = (df.groupby("wilaya", dropna=False)
                   .agg(total=("nom", "count"),
                        gps=("latitude", lambda s: s.notna().sum()),
                        telephones=("telephone", lambda s: s.astype(str).str.strip().ne("").sum()),
                        sites=("site_web", lambda s: s.astype(str).str.strip().ne("").sum()))
                   .reset_index())
        stats.to_excel(writer, index=False, sheet_name="Statistiques wilayas")

    print()
    print("=" * 80)
    print("EXPORT TERMINÉ")
    print("=" * 80)
    print(f"TOTAL UNIQUE : {len(df)}")
    print(f"GPS présents : {df['latitude'].notna().sum()}")
    print(f"Téléphones   : {df['telephone'].astype(str).str.strip().ne('').sum()}")
    print(f"Excel        : {OUT_XLSX}")
    print(f"CSV          : {OUT_CSV}")
    print(f"Checkpoint   : {CHECKPOINT}")
    print(f"Progression  : {PROGRESS}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true",
                        help="scraper toutes les wilayas")
    parser.add_argument("--wilaya", default="Mostaganem",
                        help="une wilaya précise")
    parser.add_argument("--max-results", type=int, default=80,
                        help="maximum de fiches par catégorie et wilaya")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="pause entre deux recherches")
    parser.add_argument("--visible", action="store_true",
                        help="afficher le navigateur")
    parser.add_argument("--resume", action="store_true",
                        help="reprendre depuis progression.json sans retraiter les catégories validées")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="nombre max de tentatives par catégorie (défaut: 3)")
    parser.add_argument("--base-delay", type=float, default=2.0,
                        help="délai de base pour backoff exponentiel en secondes (défaut: 2.0)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.all:
        # tolérance aux accents/casse
        matches = [w for w in WILAYAS if w.lower() == args.wilaya.lower()]
        if not matches:
            print(f"Wilaya inconnue : {args.wilaya}")
            print("Utilisez --all ou un nom présent dans WILAYAS.")
            sys.exit(2)
        args.wilaya = matches[0]

    # Un scraping national doit toujours reprendre automatiquement.
    if args.all:
        args.resume = True

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nArrêt demandé. Le checkpoint a été conservé.")