#!/usr/bin/env python3
"""
Medizy - Réparation des noms de communes corrompus dans la table `facilities`

Diagnostique:
  - 10 441 facilities ont un `commune` qui ne matche aucun `nom_fr` de la table `communes`.
  - La corruption est un `ï` (U+00EF) remplacé par un `�` (U+FFFD) dû à un mauvais
    décodage UTF-8 lors de l'import (ex: "Aïn Defla" -> "A�n Defla").
  - Le `communes` table est sain (0 corruption).

Action:
  - Pour chaque facility, si son `commune` ne matche pas un `nom_fr`, chercher le
    `nom_fr` le plus proche au sein de la même wilaya (levenshtein normalisée).
  - Corriger le `commune` et, si les coordonnées de la commune trouvée diffèrent,
    réattribuer les coordonnées GPS.
  - Générer un rapport de réparation.

Usage:
    python tools/repair_commune_names.py [--dry-run]
"""

import sqlite3
import json
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "assets" / "data" / "sante_dz_bundled.db"
REPORTS_DIR = PROJECT_ROOT / "tools" / "reports"
REPAIR_REPORT = REPORTS_DIR / "REPAIR_COMMUNE_NAMES_REPORT.json"


def normalize(s: str) -> str:
    """Supprime les caractères corrompus et normalise pour la comparaison"""
    return "".join(ch for ch in s if ord(ch) < 128 and ch.isalnum()).lower()


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(
                min(
                    prev[j] + 1,
                    cur[j - 1] + 1,
                    prev[j - 1] + (ca != cb),
                )
            )
        prev = cur
    return prev[-1]


def repair(dry_run: bool = False) -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Charger les communes de référence par wilaya
    communes_by_wilaya = {}
    for row in cur.execute(
        "SELECT wilaya_code, nom_fr, latitude, longitude FROM communes"
    ):
        communes_by_wilaya.setdefault(row["wilaya_code"], {})[row["nom_fr"]] = (
            row["latitude"],
            row["longitude"],
        )

    # Identifier les facilities dont le commune ne matche pas
    cur.execute("SELECT id, wilaya_code, commune, latitude, longitude FROM facilities")
    all_facilities = cur.fetchall()

    repaired = []
    unchanged = 0
    no_match = 0

    for fac in all_facilities:
        wilaya = fac["wilaya_code"]
        commune = fac["commune"]
        if commune is None or commune == "":
            no_match += 1
            continue

        ref_communes = communes_by_wilaya.get(wilaya, {})
        if commune in ref_communes:
            unchanged += 1
            continue

        # Recherche du nom le plus proche
        target = normalize(commune)
        best_name = None
        best_score = None
        for name, (lat, lon) in ref_communes.items():
            if lat is None or lon is None:
                continue
            score = levenshtein(target, normalize(name))
            if best_score is None or score < best_score:
                best_score = score
                best_name = name

        if best_name is None or best_score > max(6, len(target) // 2):
            no_match += 1
            continue

        new_lat, new_lon = ref_communes[best_name]
        old_lat = fac["latitude"] if fac["latitude"] is not None else 0.0
        old_lon = fac["longitude"] if fac["longitude"] is not None else 0.0
        item = {
            "id": fac["id"],
            "wilaya_code": wilaya,
            "old_commune": commune,
            "new_commune": best_name,
            "distance": best_score,
            "old_lat": old_lat,
            "old_lon": old_lon,
            "new_lat": new_lat,
            "new_lon": new_lon,
            "coords_changed": abs(old_lat - new_lat) > 1e-6
            or abs(old_lon - new_lon) > 1e-6,
        }
        repaired.append(item)

        if not dry_run:
            cur.execute(
                "UPDATE facilities SET commune = ?, latitude = ?, longitude = ? WHERE id = ?",
                (best_name, new_lat, new_lon, fac["id"]),
            )

    if not dry_run and repaired:
        conn.commit()

    conn.close()

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_facilities": len(all_facilities),
        "repaired": len(repaired),
        "unchanged": unchanged,
        "no_match": no_match,
        "dry_run": dry_run,
        "sample": repaired[:10],
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPAIR_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Réparer les noms de communes corrompus"
    )
    parser.add_argument("--dry-run", action="store_true", help="Ne pas écrire")
    args = parser.parse_args()

    report = repair(dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()