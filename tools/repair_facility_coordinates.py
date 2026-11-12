#!/usr/bin/env python3
"""
Medizy - Réparation des coordonnées GPS des facilities (Phase 4 finalisation)

Diagnostique:
  - Le CSV source Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv contient des
    coordonnées erronées pour certaines communes (ex: Adrar 01 a 35.9/3.1 au lieu de ~27.8/-0.2).
  - La table `facilities` a hérité de ces coordonnées pour 10 219 lignes, dont 1 120 pour la
    commune d'Adrar (wilaya 01) qui pointent sur Alger.
  - La table `communes` a, elle, des coordonnées correctes (centroïdes communaux).

Action:
  - Pour chaque facility, réattribuer ses coordonnées depuis la commune correspondante
    (wilaya_code + nom commune) si un match existe, sinon laisser inchangé.
  - Générer un rapport de réparation.

Usage:
    python tools/repair_facility_coordinates.py [--dry-run]
"""

import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "assets" / "data" / "sante_dz_bundled.db"
REPORTS_DIR = PROJECT_ROOT / "tools" / "reports"
REPAIR_REPORT = REPORTS_DIR / "REPAIR_COORDINATES_REPORT.json"


def repair(dry_run: bool = False) -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Charger les coordonnées de référence des communes
    communes = {}
    for row in cur.execute("SELECT wilaya_code, nom_fr, latitude, longitude FROM communes"):
        communes[(row["wilaya_code"], row["nom_fr"])] = (
            row["latitude"],
            row["longitude"],
        )

    # 2. Identifier les facilities dont les coordonnées diffèrent de leur commune
    cur.execute("""
        SELECT id, wilaya_code, commune, latitude, longitude
        FROM facilities
        WHERE commune IS NOT NULL AND commune != ''
    """)
    all_facilities = cur.fetchall()

    to_repair = []
    unchanged = 0
    no_commune_match = 0

    for fac in all_facilities:
        key = (fac["wilaya_code"], fac["commune"])
        ref = communes.get(key)
        if ref is None or ref[0] is None or ref[1] is None:
            no_commune_match += 1
            continue
        if (
            abs(fac["latitude"] - ref[0]) < 1e-6
            and abs(fac["longitude"] - ref[1]) < 1e-6
        ):
            unchanged += 1
            continue
        to_repair.append(
            {
                "id": fac["id"],
                "wilaya_code": fac["wilaya_code"],
                "commune": fac["commune"],
                "old_lat": fac["latitude"],
                "old_lon": fac["longitude"],
                "new_lat": ref[0],
                "new_lon": ref[1],
            }
        )

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_facilities": len(all_facilities),
        "to_repair": len(to_repair),
        "unchanged": unchanged,
        "no_commune_match": no_commune_match,
        "dry_run": dry_run,
        "sample": to_repair[:10],
    }

    if not dry_run and to_repair:
        for item in to_repair:
            cur.execute(
                "UPDATE facilities SET latitude = ?, longitude = ? WHERE id = ?",
                (item["new_lat"], item["new_lon"], item["id"]),
            )
        conn.commit()

    conn.close()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPAIR_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(description="Réparer les coordonnées GPS des facilities")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas écrire, juste rapporter")
    args = parser.parse_args()

    report = repair(dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()