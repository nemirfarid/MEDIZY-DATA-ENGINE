# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Auto Phase B: Scraping par commune
======================================================
Surveille la fin du scraping national et enchaîne automatiquement
sur le scraping complémentaire par commune.

Stratégie :
1. Attendre la fin du scraping national
2. Analyser les gaps avec SmartCoverageEngine
3. Générer les requêtes par commune prioritaires
4. Scraper avec mesure de rendement
5. Sauvegarder après chaque requête
"""

import asyncio
import csv
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import pandas as pd
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("DEPENDANCES MANQUANTES.")
    sys.exit(1)

# Chemins
BASE = Path(__file__).resolve().parent
EXPORTS = Path(r"D:\SANTE_DZ_EXPORTS")
EXPORTS.mkdir(exist_ok=True)

CHECKPOINT_MAIN = EXPORTS / "checkpoint.csv"
PROGRESS_MAIN = EXPORTS / "progression.json"
CHECKPOINT_PHASE_B = EXPORTS / "checkpoint_phase_b.csv"
PROGRESS_PHASE_B = EXPORTS / "progression_phase_b.json"
YIELD_LOG = EXPORTS / "yield_log.csv"

# Imports modules
sys.path.insert(0, str(BASE))
from smart_coverage_engine import SmartCoverageEngine, QueryYield
from coverage_analyzer import CoverageAnalyzer
from communes_officielles import get_communes_by_wilaya, get_all_communes
from communes_algerie import WILAYAS
from scraper import CATEGORIES  # 34 catégories
from yield_analyzer import YieldAnalyzer

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


def load_main_checkpoint() -> List[dict]:
    if not CHECKPOINT_MAIN.exists():
        return []
    try:
        return pd.read_csv(CHECKPOINT_MAIN, dtype=str).fillna("").to_dict("records")
    except Exception:
        return []


def load_main_progress() -> dict:
    if not PROGRESS_MAIN.exists():
        return {"completed": [], "current": None}
    try:
        return json.loads(PROGRESS_MAIN.read_text(encoding="utf-8"))
    except Exception:
        return {"completed": [], "current": None}


def is_national_completed() -> bool:
    """Vérifie si le scraping national est terminé."""
    prog = load_main_progress()
    completed = set(tuple(x) for x in prog.get("completed", []) if isinstance(x, list) and len(x) == 2)
    # Toutes les wilayas x toutes les catégories
    wilaya_names = [w["nom"] for w in WILAYAS]
    expected = {(w, c) for w in wilaya_names for c in CATEGORIES}
    return expected.issubset(completed)


def wait_for_national_completion(check_interval: int = 60):
    """Attend la fin du scraping national."""
    print("[WAIT] En attente de la fin du scraping national...")
    while not is_national_completed():
        prog = load_main_progress()
        completed = len(prog.get("completed", []))
        total = len(WILAYAS) * len(CATEGORIES)
        print(f"[WAIT] Progression nationale : {completed}/{total} catégories validées. Vérification dans {check_interval}s...")
        time.sleep(check_interval)
    print("[OK] Scraping national terminé. Démarrage Phase B.")


def load_phase_b_checkpoint() -> List[dict]:
    if not CHECKPOINT_PHASE_B.exists():
        return []
    try:
        return pd.read_csv(CHECKPOINT_PHASE_B, dtype=str).fillna("").to_dict("records")
    except Exception:
        return []


def save_phase_b_checkpoint(rows: List[dict]):
    if not rows:
        return
    df = pd.DataFrame(rows)
    for c in FIELDS:
        if c not in df.columns:
            df[c] = ""
    df = df[FIELDS]
    tmp = CHECKPOINT_PHASE_B.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    tmp.replace(CHECKPOINT_PHASE_B)


def load_phase_b_progress() -> dict:
    if not PROGRESS_PHASE_B.exists():
        return {"completed": [], "current": None, "updated_at": None}
    try:
        data = json.loads(PROGRESS_PHASE_B.read_text(encoding="utf-8"))
        data.setdefault("completed", [])
        data.setdefault("current", None)
        return data
    except Exception:
        return {"completed": [], "current": None, "updated_at": None}


def save_phase_b_progress(completed: List[List[str]], current: List[str] = None):
    seen = set()
    unique = []
    for x in completed:
        if isinstance(x, (list, tuple)) and len(x) == 4:
            t = tuple(x)
            if t not in seen:
                seen.add(t)
                unique.append(list(t))
    unique.sort()
    data = {
        "version": 1,
        "completed": unique,
        "current": current,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    tmp = PROGRESS_PHASE_B.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(PROGRESS_PHASE_B)


def append_yield_log(yield_data: QueryYield):
    file_exists = YIELD_LOG.exists()
    with YIELD_LOG.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "wilaya", "commune", "category", "query", "results_found",
            "new_unique", "duplicates", "new_gps", "new_phones", "yield_pct", "timestamp"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "wilaya": yield_data.wilaya,
            "commune": yield_data.commune,
            "category": yield_data.category,
            "query": yield_data.query,
            "results_found": yield_data.results_found,
            "new_unique": yield_data.new_unique,
            "duplicates": yield_data.duplicates,
            "new_gps": yield_data.new_gps,
            "new_phones": yield_data.new_phones,
            "yield_pct": yield_data.yield_pct,
            "timestamp": yield_data.timestamp,
        })


def build_phase_b_queries(max_wilayas: int = 58, max_communes_per_wilaya: int = 15, max_categories: int = 20) -> List[Dict[str, str]]:
    """
    Génère les requêtes de Phase B de manière intelligente.
    Priorité :
    1. Wilayas avec faible coverage
    2. Communes sans résultat
    3. Catégories manquantes
    """
    rows = load_main_checkpoint()
    if not rows:
        print("[ERREUR] checkpoint.csv vide. Impossible de générer les requêtes Phase B.")
        return []

    analyzer = CoverageAnalyzer(rows)
    engine = SmartCoverageEngine(rows)

    # Calculer les scores de priorité par wilaya
    wilaya_scores = analyzer.by_wilaya()
    priority_wilayas = sorted(wilaya_scores.keys(), key=lambda w: -wilaya_scores[w].get("priority_score", 0))

    # Limiter au nombre de wilayas demandé
    priority_wilayas = priority_wilayas[:max_wilayas]

    queries = []
    for wilaya in priority_wilayas:
        # Trouver le code wilaya
        wilaya_code = None
        for w in WILAYAS:
            if w["nom"] == wilaya:
                wilaya_code = str(w["code"]).zfill(2)
                break
        if not wilaya_code:
            continue

        communes = get_communes_by_wilaya(wilaya_code)
        if not communes:
            continue

        # Filtrer les communes déjà bien couvertes
        undercovered = analyzer.undercovered_communes()
        undercovered_set = {(uc["wilaya"], uc["commune"]) for uc in undercovered}

        # Trier les communes : non couvertes d'abord, puis sous-couvertes
        sorted_communes = []
        for c in communes:
            key = (wilaya, c["nom_fr"])
            if key not in undercovered_set:
                sorted_communes.append(c)
        for c in communes:
            key = (wilaya, c["nom_fr"])
            if key in undercovered_set:
                sorted_communes.append(c)

        # Limiter le nombre de communes
        sorted_communes = sorted_communes[:max_communes_per_wilaya]

        # Catégories prioritaires : celles avec le moins de résultats
        wilaya_rows = [r for r in rows if r.get("wilaya", "").strip() == wilaya]
        cat_counts = {}
        for r in wilaya_rows:
            cat = r.get("categorie_recherche", "").strip()
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        # Trier les catégories par nombre croissant de résultats
        sorted_cats = sorted(CATEGORIES[:max_categories], key=lambda c: cat_counts.get(c, 0))

        for commune in sorted_communes:
            for cat in sorted_cats[:max_categories]:
                queries.append({
                    "wilaya": wilaya,
                    "wilaya_code": wilaya_code,
                    "commune": commune["nom_fr"],
                    "category": cat,
                    "query": f"{cat} {commune['nom_fr']} {wilaya} Algérie"
                })

    print(f"[PHASE B] Requêtes générées : {len(queries)}")
    return queries


async def search_commune_category(page, wilaya, commune, category, max_results=60):
    """Scrape une recherche wilaya + commune + catégorie."""
    query = f"{category} {commune} {wilaya} Algérie"
    url = "https://www.google.com/maps/search/" + re.sub(r"\s+", "+", query) + "?hl=fr"

    rows = []
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1800)

        panel = page.locator('div[role="feed"]').first
        if not await panel.count():
            return rows, 0

        seen_urls = set()
        for scroll_no in range(20):
            cards = panel.locator('div[role="article"]')
            count = await cards.count()

            for i in range(count):
                try:
                    card = cards.nth(i)
                    link = card.locator("a.hfpxzc").first
                    href = await link.get_attribute("href") if await link.count() else ""
                    name = await card.locator("div.qBF1Pd").first.get_attribute("aria-label") if await card.locator("div.qBF1Pd").count() else ""
                    if not name:
                        name = await card.locator("div.qBF1Pd").first.inner_text() if await card.locator("div.qBF1Pd").count() else ""

                    if not name and not href:
                        continue
                    key = href or name
                    if key in seen_urls:
                        continue
                    seen_urls.add(key)

                    txt = await card.inner_text()
                    lines = [clean(x) for x in txt.splitlines() if clean(x)]

                    phone = ""
                    phone_re = re.compile(r"(?:\+213|0)(?:[\s.-]?\d){8,10}")
                    for line in lines:
                        m = phone_re.search(line)
                        if m:
                            phone = clean(m.group(0))
                            break

                    lat, lng = extract_lat_lng(href)

                    rows.append({
                        "wilaya": wilaya,
                        "commune": commune,
                        "categorie_recherche": category,
                        "nom": name,
                        "adresse": lines[1] if len(lines) > 1 else "",
                        "telephone": phone,
                        "site_web": "",
                        "note": "",
                        "nombre_avis": "",
                        "horaires": "",
                        "latitude": lat,
                        "longitude": lng,
                        "google_maps_url": href,
                        "place_id_si_visible": "",
                        "type_google": "",
                        "statut": "visible",
                        "scrape_date": datetime.now().isoformat(timespec="seconds"),
                        "source": "Google Maps public UI - Phase B",
                    })
                    if len(rows) >= max_results:
                        break
                except Exception:
                    continue

            if len(rows) >= max_results:
                break
            try:
                await panel.evaluate("(el) => el.scrollTo(0, el.scrollHeight)")
            except Exception:
                break
            await page.wait_for_timeout(900)

    except PlaywrightTimeoutError:
        pass
    except Exception:
        pass

    return rows, len(rows)


async def run_phase_b(args):
    print("=" * 80)
    print("MEDIZY — PHASE B : SCRAPING PAR COMMUNE")
    print("=" * 80)

    # Attendre la fin du scraping national
    if args.wait_national:
        wait_for_national_completion(check_interval=args.wait_interval)

    # Charger les données existantes
    main_rows = load_main_checkpoint()
    print(f"Checkpoint principal : {len(main_rows)} fiches")

    # Générer les requêtes
    queries = build_phase_b_queries(
        max_wilayas=args.max_wilayas,
        max_communes_per_wilaya=args.max_communes,
        max_categories=args.max_categories
    )
    if not queries:
        print("[ERREUR] Aucune requête générée. Fin.")
        return

    # Charger la progression Phase B
    phase_b_prog = load_phase_b_progress()
    phase_b_completed = set(tuple(x) for x in phase_b_prog.get("completed", []) if isinstance(x, list) and len(x) == 4)
    phase_b_rows = load_phase_b_checkpoint()

    # Filtrer les requêtes déjà complétées
    pending = [q for q in queries if (q["wilaya"], q["commune"], q["category"], q["query"]) not in phase_b_completed]
    print(f"Requêtes en attente : {len(pending)} / {len(queries)}")

    if not pending:
        print("[OK] Toutes les requêtes Phase B sont déjà complétées.")
        return

    yield_analyzer = YieldAnalyzer(
        min_new_per_query=args.min_new_per_query,
        max_empty_streak=args.max_empty_streak,
        min_yield_pct=args.min_yield_pct
    )

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
            for idx, q in enumerate(pending, 1):
                wilaya = q["wilaya"]
                commune = q["commune"]
                category = q["category"]
                query = q["query"]

                print(f"\n[{idx}/{len(pending)}] {wilaya} | {commune} | {category}")

                rows, results_found = await search_commune_category(page, wilaya, commune, category, args.max_results)

                # Mesurer le rendement
                new_unique = 0
                duplicates = 0
                new_gps = 0
                new_phones = 0

                if rows:
                    # Déduplication avec le checkpoint principal
                    seen_keys = set()
                    for r in main_rows + phase_b_rows:
                        key = r.get("google_maps_url", "") or r.get("nom", "")
                        seen_keys.add(key)

                    for r in rows:
                        key = r.get("google_maps_url", "") or r.get("nom", "")
                        if key in seen_keys:
                            duplicates += 1
                        else:
                            new_unique += 1
                            seen_keys.add(key)
                            if r.get("latitude") and r.get("longitude"):
                                new_gps += 1
                            if r.get("telephone"):
                                new_phones += 1
                            phase_b_rows.append(r)

                    # Sauvegarder
                    save_phase_b_checkpoint(phase_b_rows)
                    phase_b_completed.add((wilaya, commune, category, query))
                    save_phase_b_progress([list(x) for x in phase_b_completed], None)

                yield_pct = round(100.0 * new_unique / results_found, 2) if results_found else 0.0
                yield_data = QueryYield(
                    wilaya=wilaya,
                    commune=commune,
                    category=category,
                    query=query,
                    results_found=results_found,
                    new_unique=new_unique,
                    duplicates=duplicates,
                    new_gps=new_gps,
                    new_phones=new_phones,
                    yield_pct=yield_pct,
                )
                yield_analyzer.record(yield_data)
                append_yield_log(yield_data)

                print(f"    -> found={results_found} | new={new_unique} | dup={duplicates} | yield={yield_pct}%")

                # Vérifier si on doit arrêter cette catégorie/commune
                if yield_analyzer.should_stop_category(wilaya, commune, category):
                    print(f"    [STOP] Rendement insuffisant pour {wilaya}/{commune}/{category}")
                    # Marquer toutes les variantes restantes comme complétées pour éviter de retraiter
                    remaining = [q2 for q2 in pending if q2["wilaya"] == wilaya and q2["commune"] == commune and q2["category"] == category]
                    for q2 in remaining:
                        phase_b_completed.add((q2["wilaya"], q2["commune"], q2["category"], q2["query"]))
                    save_phase_b_progress([list(x) for x in phase_b_completed], None)

                await asyncio.sleep(args.delay)

        except KeyboardInterrupt:
            save_phase_b_checkpoint(phase_b_rows)
            save_phase_b_progress([list(x) for x in phase_b_completed], None)
            print("\n[STOP] Phase B interrompue. Données sauvegardées.")
            raise
        finally:
            await context.close()
            await browser.close()

    # Export final Phase B
    if phase_b_rows:
        df = pd.DataFrame(phase_b_rows)
        for c in FIELDS:
            if c not in df.columns:
                df[c] = ""
        df = df[FIELDS].drop_duplicates(subset=["nom", "adresse", "telephone", "latitude", "longitude"])
        out_csv = EXPORTS / "SANTE_DZ_GOOGLE_MAPS_PHASE_B.csv"
        out_xlsx = EXPORTS / "SANTE_DZ_GOOGLE_MAPS_PHASE_B.xlsx"
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Phase B")
        print(f"\n[EXPORT] Phase B terminée : {len(df)} fiches uniques")
        print(f"  CSV  : {out_csv}")
        print(f"  XLSX : {out_xlsx}")

    print("\n[OK] Phase B terminée.")


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-national", action="store_true", help="attendre la fin du scraping national")
    parser.add_argument("--wait-interval", type=int, default=60, help="intervalle de vérification en secondes")
    parser.add_argument("--max-wilayas", type=int, default=58, help="nombre max de wilayas à traiter")
    parser.add_argument("--max-communes", type=int, default=15, help="nombre max de communes par wilaya")
    parser.add_argument("--max-categories", type=int, default=20, help="nombre max de catégories par commune")
    parser.add_argument("--max-results", type=int, default=60, help="max fiches par recherche")
    parser.add_argument("--delay", type=float, default=2.0, help="pause entre requêtes")
    parser.add_argument("--visible", action="store_true", help="afficher le navigateur")
    parser.add_argument("--min-new-per-query", type=int, default=3, help="minimum nouvelles fiches par requête")
    parser.add_argument("--max-empty-streak", type=int, default=3, help="requêtes vides avant arrêt")
    parser.add_argument("--min-yield-pct", type=float, default=5.0, help="rendement minimum (pourcentage)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(run_phase_b(args))
    except KeyboardInterrupt:
        print("\n[STOP] Phase B interrompue.")
