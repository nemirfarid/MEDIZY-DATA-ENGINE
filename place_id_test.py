# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Place ID Coherence Test
============================================
Vérifie que les place_id sont :
- bien formés
- réellement distincts
- non accidentellement identiques pour plusieurs fiches différentes
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List


def validate_place_id(pid: str) -> bool:
    """Un place_id Google Maps valide commence par ChIJ et fait au moins 10 caractères."""
    if not pid:
        return False
    return bool(re.match(r"^ChIJ[A-Za-z0-9_-]{10,}$", pid))


def analyze_place_ids(rows: List[dict]) -> Dict[str, Any]:
    place_ids = [r.get("place_id_si_visible", "").strip() for r in rows if r.get("place_id_si_visible", "").strip()]
    
    valid = [pid for pid in place_ids if validate_place_id(pid)]
    invalid = [pid for pid in place_ids if not validate_place_id(pid)]
    
    counter = Counter(place_ids)
    duplicates = {pid: count for pid, count in counter.items() if count > 1}
    
    # Vérifier si les doublons sont des fiches vraiment différentes
    suspicious = []
    for pid, count in duplicates.items():
        rows_with_pid = [r for r in rows if r.get("place_id_si_visible", "").strip() == pid]
        names = [r.get("nom", "").strip() for r in rows_with_pid]
        if len(set(names)) > 1:
            suspicious.append({
                "place_id": pid,
                "count": count,
                "names": names,
                "reason": "Même place_id pour des noms différents"
            })
    
    return {
        "total_rows": len(rows),
        "place_id_present": len(place_ids),
        "place_id_valid": len(valid),
        "place_id_invalid": len(invalid),
        "unique_place_ids": len(set(place_ids)),
        "duplicate_place_ids": len(duplicates),
        "suspicious_duplicates": len(suspicious),
        "coverage_pct": round(100.0 * len(place_ids) / len(rows), 2) if rows else 0.0,
        "invalid_samples": invalid[:10],
        "suspicious_samples": suspicious[:10],
    }


def test_place_id_coherence(csv_path: Path) -> Dict[str, Any]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return analyze_place_ids(rows)


if __name__ == "__main__":
    csv_path = Path(r"D:\SANTE_DZ_EXPORTS\checkpoint.csv")
    report = test_place_id_coherence(csv_path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
