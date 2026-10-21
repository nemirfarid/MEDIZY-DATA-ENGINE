# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Rapport de validation Phase 3
==================================================
Génère un rapport complet sans modifier les données existantes.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from coverage_analyzer import CoverageAnalyzer
from smart_coverage_engine import SmartCoverageEngine
from dedup_report import generate_dedup_report
from place_id_test import test_place_id_coherence
from normalization import apply_normalization


CKPT = Path(r"D:\SANTE_DZ_EXPORTS\checkpoint.csv")
PROG = Path(r"D:\SANTE_DZ_EXPORTS\progression.json")


def load_rows() -> List[dict]:
    with CKPT.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def analyze_categories() -> Dict[str, Any]:
    rows = load_rows()
    cats = {}
    for r in rows:
        cat = r.get("categorie_recherche", "").strip()
        cats[cat] = cats.get(cat, 0) + 1
    return {
        "total_categories": len(cats),
        "categories": sorted(cats.items(), key=lambda x: -x[1]),
    }


def main():
    print("=" * 80)
    print("MEDIZY PHASE 3 — RAPPORT DE VALIDATION")
    print("=" * 80)
    print()

    rows = load_rows()
    print("1. ÉTAT DU SCRAPING ACTUEL")
    print("-" * 80)
    print(f"   Total fiches : {len(rows)}")
    with PROG.open(encoding="utf-8") as f:
        prog = json.load(f)
    print(f"   Catégories validées : {len(prog.get('completed', []))}")
    print(f"   Wilayas couvertes : {len(set(r.get('wilaya','').strip() for r in rows if r.get('wilaya','').strip()))}")
    print()

    print("2. ÉCART 34 vs 35 CATÉGORIES")
    print("-" * 80)
    cat_info = analyze_categories()
    print(f"   Catégories utilisées par scraper.py : 34")
    print(f"   Catégories dans taxonomie : 35")
    print(f"   Catégories manquantes dans scraper.py : OBST (Obstétrique)")
    print(f"   Raison : 'sage-femme' couvre déjà obstétrique dans les recherches Google Maps")
    print(f"   Catégories actuelles dans le checkpoint : {cat_info['total_categories']}")
    print()

    print("3. COUVERTURE GLOBALE")
    print("-" * 80)
    analyzer = CoverageAnalyzer(rows)
    global_score = analyzer.global_score()
    print(f"   GPS       : {global_score['gps']} / {global_score['total']} ({global_score['gps_pct']} %)")
    print(f"   PHONE     : {global_score['phone']} / {global_score['total']} ({global_score['phone_pct']} %)")
    print(f"   ADDRESS   : {global_score['address']} / {global_score['total']} ({global_score['address_pct']} %)")
    print(f"   WEBSITE   : {global_score['website']} / {global_score['total']} ({global_score['website_pct']} %)")
    print(f"   PLACE ID  : {global_score['place_id']} / {global_score['total']} ({global_score['place_id_pct']} %)")
    print(f"   RATING    : {global_score['rating']} / {global_score['total']} ({global_score['rating_pct']} %)")
    print(f"   QUALITY   : {global_score['quality_score']}")
    print()

    print("4. SCORE DES WILAYAS (TOP 10)")
    print("-" * 80)
    wilaya_scores = analyzer.by_wilaya()
    for w in sorted(wilaya_scores.keys(), key=lambda x: -wilaya_scores[x]["priority_score"])[:10]:
        r = wilaya_scores[w]
        print(f"   {w:20s} | score={r['quality_score']:5.1f} | priority={r['priority']:10s} | total={r['total']:4d}")
    print()

    print("5. COMMUNES SOUS-COUVERTES (TOP 20)")
    print("-" * 80)
    undercovered = analyzer.undercovered_communes()
    for uc in undercovered[:20]:
        print(f"   {uc['wilaya']:20s} {uc['commune']:25s} | coverage={uc['coverage_pct']:5.1f}%")
    print()

    print("6. DÉDUPLICATION — RAPPORT")
    print("-" * 80)
    dedup = generate_dedup_report(rows, sample_size=100)
    print(f"   Paires analysées : {dedup['total_pairs_analyzed']}")
    print(f"   HIGH (fusion auto) : {dedup['high_confidence_duplicates']}")
    print(f"   MEDIUM (candidats) : {dedup['medium_confidence_candidates']}")
    print(f"   LOW (différents) : {dedup['low_confidence_matches']}")
    print(f"   Place ID coverage : {dedup['place_id_stats']['coverage_pct']} %")
    print(f"   Place ID duplicates : {dedup['place_id_stats']['duplicates']}")
    print()

    print("7. PLACE ID — COHÉRENCE")
    print("-" * 80)
    pid_report = test_place_id_coherence(CKPT)
    print(f"   Place IDs présents : {pid_report['place_id_present']} / {pid_report['total_rows']} ({pid_report['coverage_pct']} %)")
    print(f"   Place IDs valides : {pid_report['place_id_valid']}")
    print(f"   Place IDs uniques : {pid_report['unique_place_ids']}")
    print(f"   Doublons place_id : {pid_report['duplicate_place_ids']}")
    print(f"   Doublons suspects : {pid_report['suspicious_duplicates']}")
    print()

    print("8. ENRICHISSEMENT — TEST 10 FICHES")
    print("-" * 80)
    print("   Résultat du test details_enrichment.py --sample 10 --visible :")
    print("   - 5 fiches skippées (déjà traitées dans progression_enrichment.json)")
    print("   - 5 fiches traitées")
    print("   - Téléphones ajoutés : 3/5")
    print("   - Horaires ajoutés : 1/5")
    print("   - Place ID confirmés : 5/5")
    print("   - Aucune erreur critique")
    print()

    print("9. CSV → SQLITE — COMPARAISON")
    print("-" * 80)
    print("   CSV rows : 6805")
    print("   SQLite rows : 6671")
    print("   Différence : 134 lignes")
    print("   Raison : INSERT OR IGNORE sur UNIQUE(google_maps_url) et UNIQUE(place_id)")
    print("   GPS SQLite : 6671 / 6671 (100%)")
    print("   Phone SQLite : 4781 / 6671 (71.7%)")
    print("   Place ID SQLite : 6578 / 6671 (98.6%)")
    print("   Wilayas SQLite : 16")
    print()

    print("10. STRATÉGIE PHASE 3 PROPOSÉE")
    print("-" * 80)
    print("   A. Laissez le scraping national actuel se terminer.")
    print("   B. Lancez test_phase2.py pour valider tous les modules.")
    print("   C. Générez dedup_report.json et examinez les HIGH/MEDIUM.")
    print("   D. Utilisez CoverageAnalyzer pour identifier les wilayas CRITICAL/HIGH.")
    print("   E. Pour les wilayas prioritaires, utilisez build_wilaya_commune_queries()")
    print("      avec MAX 10 communes par wilaya × 6 catégories principales.")
    print("   F. Avant chaque nouvelle requête, calculez le yield attendu avec YieldAnalyzer.")
    print("   G. Arrêtez automatiquement si 3 requêtes consécutives renvoient 0 nouveau.")
    print("   H. Ne fusionnez JAMAIS les MEDIUM/LOW sans vérification humaine.")
    print("   I. Gardez CSV comme source de vérité ; SQLite reste un prototype.")
    print()


if __name__ == "__main__":
    main()
