#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — CLI d'Exécution du Pipeline d'Ingestion & Enrichissement
============================================================================
Script exécutable à la racine permettant de lancer l'ingestion soit sur des wilayas
spécifiques (ex: 16 Alger, 31 Oran, 27 Mostaganem), soit sur les 58 wilayas d'Algérie.

Exemples d'utilisation :
  python run_ingest.py --wilayas 16 31 27
  python run_ingest.py --wilayas Alger Oran Mostaganem
  python run_ingest.py --all
  python run_ingest.py --wilayas 16 --google
  python run_ingest.py --wilayas 16 --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import List, Optional

from medizy_pipeline.enrichment.ingest_pipeline import (
    ALGERIAN_WILAYAS,
    FacilityDataStore,
    HealthEnrichmentPipeline,
    IngestionReport,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("medizy.run_ingest")


def print_banner():
    print("""
==============================================================================
    MEDIZY / SANTÉ DZ — Pipeline National d'Enrichissement Cartographique
    Intégration des hôpitaux, cliniques et polycliniques (58 Wilayas)
==============================================================================
    """)


def execute_ingestion(
    wilayas: Optional[List[str]] = None,
    all_wilayas: bool = False,
    use_google: bool = False,
    db_url: Optional[str] = None,
    dry_run: bool = False,
    delay: float = 2.0,
    report_file: Optional[str] = None,
) -> IngestionReport:
    """Exécute le pipeline d'ingestion avec gestion du rate-limiting et déduplication."""
    print_banner()

    # Détermination des wilayas cibles
    target_wilayas: List[str] = []
    if all_wilayas:
        target_wilayas = [w["code"] for w in ALGERIAN_WILAYAS]
        logger.info("Mode sélectionné : Intégralité des 58 wilayas d'Algérie.")
    elif wilayas:
        target_wilayas = wilayas
        logger.info(f"Mode sélectionné : Wilayas cibles [{', '.join(target_wilayas)}].")
    else:
        # Par défaut, wilayas pilotes prioritaires (Alger, Oran, Mostaganem)
        target_wilayas = ["16", "31", "27"]
        logger.info("Aucune wilaya spécifiée. Utilisation des wilayas pilotes par défaut : 16 (Alger), 31 (Oran), 27 (Mostaganem).")

    if dry_run:
        logger.info("Mode DRY-RUN activé : aucune écriture définitive en base.")

    datastore = FacilityDataStore(db_url=db_url)
    pipeline = HealthEnrichmentPipeline(
        datastore=datastore,
        google_api_key=os.environ.get("GOOGLE_PLACES_API_KEY") if use_google else None,
    )

    start_time = time.time()
    report = IngestionReport()

    # Filtrage des wilayas
    selected_objs = [
        w for w in ALGERIAN_WILAYAS
        if w["code"] in target_wilayas or w["name"].lower() in [tw.lower() for tw in target_wilayas]
    ]

    print("\n" + "-" * 78)
    print(f"{'Code':<6} | {'Wilaya':<20} | {'Collectés':<10} | {'Insérés':<10} | {'Doublons':<10} | {'Erreurs':<8}")
    print("-" * 78)

    for w_obj in selected_objs:
        w_code = w_obj["code"]
        w_name = w_obj["name"]

        try:
            if dry_run:
                candidates = pipeline.osm_client.fetch_wilaya_facilities(wilaya_name=w_name, bbox=w_obj.get("bbox"))
                stats = {"fetched": len(candidates), "inserted": len(candidates), "duplicates": 0, "errors": 0}
            else:
                stats = pipeline.run_for_wilaya(w_obj, use_google=use_google)

            report.wilaya_stats[w_name] = stats
            report.total_fetched += stats["fetched"]
            report.total_new_inserted += stats["inserted"]
            report.total_duplicates_skipped += stats["duplicates"]
            report.total_errors += stats["errors"]

            print(
                f"{w_code:<6} | {w_name:<20} | {stats['fetched']:<10} | "
                f"{stats['inserted']:<10} | {stats['duplicates']:<10} | {stats['errors']:<8}"
            )

            # Respect du rate limiting pour ne pas surcharger les serveurs Overpass
            time.sleep(delay)

        except Exception as e:
            logger.error(f"Erreur lors du traitement de la wilaya {w_name} ({w_code}): {e}")
            report.total_errors += 1

    elapsed = time.time() - start_time
    print("-" * 78)
    print(f"TOTAL  | {len(selected_objs)} wilayas traitées | "
          f"{report.total_fetched:<10} | {report.total_new_inserted:<10} | "
          f"{report.total_duplicates_skipped:<10} | {report.total_errors:<8}")
    print("-" * 78)
    print(f"Durée totale d'exécution : {elapsed:.2f} secondes.\n")

    # Récupération et affichage du tableau récapitulatif par typologie
    typologies = datastore.get_typology_breakdown_by_wilaya()
    print("=" * 86)
    print(f"{'Wilaya':<22} | {'CHU':<5} | {'EPH':<5} | {'EPSP':<5} | {'Poly':<6} | {'Clinique':<9} | {'Autres':<8} | {'Total':<6}")
    print("=" * 86)
    national_chu = 0
    national_eph = 0
    national_epsp = 0
    national_poly = 0
    national_clinique = 0
    national_total = 0

    for w_name, counts in sorted(typologies.items()):
        chu = counts.get("CHU", 0)
        eph = counts.get("EPH", 0)
        epsp = counts.get("EPSP", 0)
        poly = counts.get("Polyclinique", 0)
        clinique = counts.get("Clinique", 0)
        autres = sum(v for k, v in counts.items() if k not in ("CHU", "EPH", "EPSP", "Polyclinique", "Clinique"))
        w_total = sum(counts.values())

        national_chu += chu
        national_eph += eph
        national_epsp += epsp
        national_poly += poly
        national_clinique += clinique
        national_total += w_total

        print(f"{w_name:<22} | {chu:<5} | {eph:<5} | {epsp:<5} | {poly:<6} | {clinique:<9} | {autres:<8} | {w_total:<6}")

    print("=" * 86)
    print(f"{'TOTAL NATIONAL':<22} | {national_chu:<5} | {national_eph:<5} | {national_epsp:<5} | {national_poly:<6} | {national_clinique:<9} | {sum(sum(c.values()) for c in typologies.values()) - (national_chu + national_eph + national_epsp + national_poly + national_clinique):<8} | {national_total:<6}")
    print("=" * 86 + "\n")

    # Enregistrement du rapport
    if report_file:
        out_data = {
            "execution_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_seconds": round(elapsed, 2),
            "total_fetched": report.total_fetched,
            "total_inserted": report.total_new_inserted,
            "total_duplicates_skipped": report.total_duplicates_skipped,
            "total_errors": report.total_errors,
            "wilayas": report.wilaya_stats,
            "typology_breakdown": typologies,
            "national_totals": {
                "CHU": national_chu,
                "EPH": national_eph,
                "EPSP": national_epsp,
                "Polyclinique": national_poly,
                "Clinique": national_clinique,
                "Total": national_total,
            }
        }
        with open(report_file, "w", encoding="utf-8") as rf:
            json.dump(out_data, rf, indent=2, ensure_ascii=False)
        logger.info(f"Rapport de synthèse national enregistré dans : {report_file}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="CLI d'ingestion et d'enrichissement cartographique des structures de santé MEDIZY",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--wilayas",
        nargs="*",
        help="Codes ou noms des wilayas à traiter (ex: --wilayas 16 31 27 ou --wilayas Alger Oran Mostaganem)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Lancer l'ingestion sur l'ensemble des 58 wilayas d'Algérie",
    )
    parser.add_argument(
        "--google",
        action="store_true",
        help="Activer la recherche Google Places en tandem avec OpenStreetMap",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Chaîne de connexion PostgreSQL / PostGIS (ex: postgresql://user:pass@localhost:5432/medizy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler la collecte sans persister en base de données",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Délai en secondes entre deux requêtes Overpass (défaut: 2.0s)",
    )
    parser.add_argument(
        "--report-file",
        type=str,
        default="rapport_national_58_wilayas.json",
        help="Chemin du fichier JSON de synthèse (défaut: rapport_national_58_wilayas.json)",
    )

    args = parser.parse_args()

    execute_ingestion(
        wilayas=args.wilayas,
        all_wilayas=args.all,
        use_google=args.google,
        db_url=args.db_url,
        dry_run=args.dry_run,
        delay=args.delay,
        report_file=args.report_file,
    )


if __name__ == "__main__":
    main()
