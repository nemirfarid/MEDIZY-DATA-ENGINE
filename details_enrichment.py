# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Details Enrichment Module
==============================================
Objectif : enrichir les fiches existantes avec des données supplémentaires
disponibles sur la page détaillée Google Maps :

- horaires d'ouverture
- place_id (si disponible)
- téléphones supplémentaires
- services / description

Caractéristiques :
- OPTIONNEL : ne casse pas le scraping principal
- REPRENABLE : lit/écrit son propre checkpoint
- LIMITÉ : traite seulement les fiches sélectionnées
- CHECKPOINTÉ : sauvegarde après chaque fiche

Usage :
    python details_enrichment.py --sample 10
    python details_enrichment.py --wilaya Bouira --category pharmacie
    python details_enrichment.py --all --limit 500
"""

import argparse
import asyncio
import csv
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import pandas as pd
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("DEPENDANCES MANQUANTES. Lancez : python -m pip install -r requirements.txt")
    sys.exit(1)

BASE = Path(__file__).resolve().parent
EXPORTS = Path(r"D:\SANTE_DZ_EXPORTS")
EXPORTS.mkdir(exist_ok=True)

CHECKPOINT_SOURCE = EXPORTS / "checkpoint.csv"
CHECKPOINT = EXPORTS / "checkpoint_enrichment.csv"
PROGRESS = EXPORTS / "progression_enrichment.json"

FIELDS = [
    "wilaya", "commune", "categorie_recherche", "nom", "adresse",
    "telephone", "site_web", "note", "nombre_avis", "horaires",
    "latitude", "longitude", "google_maps_url", "place_id_si_visible",
    "type_google", "statut", "scrape_date", "source"
]


def clean(s):
    if s is None:
        return ""
    s = str(s).replace("\u200b", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


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


def load_checkpoint():
    source = CHECKPOINT_SOURCE
    target = CHECKPOINT
    # Si le checkpoint d'enrichissement n'existe pas, copier depuis le source
    if not target.exists() and source.exists():
        import shutil
        shutil.copy2(source, target)
        print(f"[INFO] Copie du checkpoint source vers {target}")
    if not target.exists():
        return []
    try:
        return pd.read_csv(target, dtype=str).fillna("").to_dict("records")
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
    seen = set()
    unique = []
    for x in completed:
        if isinstance(x, (list, tuple)) and len(x) == 2:
            t = tuple(x)
            if t not in seen:
                seen.add(t)
                unique.append(list(t))
    data = {
        "version": 1,
        "completed": unique,
        "current": current,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    tmp = PROGRESS.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(PROGRESS)


async def extract_detail_enriched(page, row):
    """Ouvre la fiche et récupère horaires, place_id, téléphones supplémentaires."""
    url = row.get("google_maps_url") or ""
    if not url:
        return row

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1500)

        final_url = page.url
        row["google_maps_url"] = final_url
        lat, lng = extract_lat_lng(final_url)
        if lat is not None:
            row["latitude"], row["longitude"] = lat, lng

        # Nom
        title = await page.locator("h1").first.inner_text()
        if title:
            row["nom"] = clean(title)

        # Récupération des boutons/liens visibles
        buttons = page.locator("button")
        n = min(await buttons.count(), 150)
        texts = []
        for i in range(n):
            try:
                t = await buttons.nth(i).get_attribute("aria-label")
                if t:
                    texts.append(clean(t))
            except Exception:
                pass

        # Horaires : chercher des motifs d'heures dans les aria-label
        hours_candidates = [t for t in texts if re.search(r"\d{1,2}:\d{2}", t)]
        if hours_candidates:
            row["horaires"] = "; ".join(hours_candidates[:5])

        # Place ID : chercher dans le HTML
        html = await page.content()
        m = re.search(r"ChIJ[A-Za-z0-9_-]{10,}", html)
        if m:
            row["place_id_si_visible"] = m.group(0)

        # Téléphone : chercher dans les boutons et liens
        phone_re = re.compile(r"(?:\+213|0)(?:[\s.-]?\d){8,10}")
        for t in texts:
            m = phone_re.search(t)
            if m:
                row["telephone"] = clean(m.group(0))
                break
        if not row.get("telephone"):
            links = page.locator("a")
            n = min(await links.count(), 100)
            for i in range(n):
                try:
                    href = await links.nth(i).get_attribute("href")
                    txt = clean(await links.nth(i).inner_text())
                    if phone_re.search(txt):
                        row["telephone"] = phone_re.search(txt).group(0)
                        break
                except Exception:
                    pass

        # Adresse / site web depuis les liens
        links = page.locator("a")
        n = min(await links.count(), 100)
        for i in range(n):
            try:
                href = await links.nth(i).get_attribute("href")
                txt = clean(await links.nth(i).inner_text())
                if href and href.startswith("http") and "google." not in href:
                    if not row.get("site_web"):
                        row["site_web"] = href
                if any(k in txt.lower() for k in ["adresse", "address", "itinéraire", "directions"]):
                    if not row.get("adresse"):
                        row["adresse"] = txt
            except Exception:
                pass

    except PlaywrightTimeoutError:
        row["statut"] = "timeout"
    except Exception as e:
        row["statut"] = "erreur: " + clean(str(e))[:180]

    row["scrape_date"] = datetime.now().isoformat(timespec="seconds")
    return row


async def run(args):
    # Charger les données existantes
    all_rows = load_checkpoint()
    progress = load_progress()
    completed = set(tuple(x) for x in progress.get("completed", []) if isinstance(x, list) and len(x) == 2)

    print("=" * 80)
    print("MEDIZY — DETAILS ENRICHMENT MODULE")
    print("=" * 80)
    print(f"Checkpoint  : {CHECKPOINT}")
    print(f"Progression : {PROGRESS}")
    print(f"Fiches existantes : {len(all_rows)}")
    print()

    # Sélectionner les fiches à enrichir
    if args.sample:
        targets = all_rows[:args.sample]
    elif args.wilaya:
        targets = [r for r in all_rows if r.get("wilaya", "").lower() == args.wilaya.lower()]
    elif args.category:
        targets = [r for r in all_rows if r.get("categorie_recherche", "").lower() == args.category.lower()]
    elif args.limit:
        targets = all_rows[:args.limit]
    else:
        # Par défaut : seulement les fiches sans horaires ni place_id
        targets = [r for r in all_rows if not str(r.get("horaires", "")).strip() or not str(r.get("place_id_si_visible", "")).strip()]

    print(f"Cibles à enrichir : {len(targets)}")
    if not targets:
        print("Aucune cible. Fin.")
        return

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

        for idx, row in enumerate(targets, 1):
            key = (row.get("wilaya", ""), row.get("categorie_recherche", ""))
            if key in completed:
                print(f"[SKIP] {idx}/{len(targets)} : {row.get('nom', '')[:50]}")
                continue

            print(f"[{idx}/{len(targets)}] {row.get('nom', '')[:50]} ...")
            try:
                enriched = await extract_detail_enriched(page, row)
                # Mettre à jour dans all_rows
                for i, r in enumerate(all_rows):
                    if r.get("google_maps_url") == row.get("google_maps_url") and r.get("nom") == row.get("nom"):
                        all_rows[i] = enriched
                        break
                else:
                    all_rows.append(enriched)
                completed.add(key)
                save_checkpoint(all_rows)
                save_progress([list(x) for x in completed], None)
                print(f"    -> OK | tel: {enriched.get('telephone','')} | horaires: {bool(enriched.get('horaires'))} | place_id: {bool(enriched.get('place_id_si_visible'))}")
            except Exception as e:
                print(f"    -> ERREUR: {e}")
                continue

            await asyncio.sleep(random.uniform(1.0, 2.5))

        await context.close()
        await browser.close()

    print()
    print("=" * 80)
    print("ENRICHISSEMENT TERMINÉ")
    print("=" * 80)
    print(f"Fiches traitées : {len(completed)}")
    print(f"Checkpoint      : {CHECKPOINT}")
    print(f"Progression     : {PROGRESS}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="traiter N fiches seulement")
    parser.add_argument("--wilaya", default="", help="filtrer par wilaya")
    parser.add_argument("--category", default="", help="filtrer par catégorie")
    parser.add_argument("--limit", type=int, default=0, help="traiter les N premières fiches")
    parser.add_argument("--visible", action="store_true", help="afficher le navigateur")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nArrêt demandé. Données conservées.")
