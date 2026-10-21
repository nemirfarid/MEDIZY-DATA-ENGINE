# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Deduplication Report Generator
===================================================
Génère un rapport de déduplication sans fusion destructive.

Produit :
- dedup_report.json
  - HIGH : paires à fusionner automatiquement
  - MEDIUM : candidats à vérification manuelle
  - LOW : établissements probablement différents

IMPORTANT :
- Ne modifie PAS checkpoint.csv
- Ne fusionne PAS automatiquement les MEDIUM/LOW
"""

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from deduplication import compute_similarity_score, AUTO_MERGE_THRESHOLD, CANDIDATE_THRESHOLD
from normalization import apply_normalization, normalize_phone_raw, normalize_text


def _stable_key_legacy(row: dict) -> str:
    raw = "|".join([
        normalize_text(row.get("nom", "")),
        normalize_text(row.get("adresse", "")),
        normalize_phone_raw(row.get("telephone", "")),
        str(row.get("latitude") or ""),
        str(row.get("longitude") or ""),
    ]).lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def generate_dedup_report(rows: List[dict], sample_size: int = 500) -> Dict[str, Any]:
    """
    Génère un rapport de déduplication.
    Pour les performances, analyse un échantillon stratifié si la liste est grande.
    """
    # Échantillonnage simple si nécessaire
    if len(rows) > sample_size:
        step = len(rows) // sample_size
        sample = rows[::step][:sample_size]
    else:
        sample = rows

    high = []
    medium = []
    low = []

    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            a = sample[i]
            b = sample[j]
            score, niveau, raisons = compute_similarity_score(a, b)
            pair = {
                "index_a": i,
                "index_b": j,
                "nom_a": a.get("nom", ""),
                "nom_b": b.get("nom", ""),
                "wilaya_a": a.get("wilaya", ""),
                "wilaya_b": b.get("wilaya", ""),
                "score": score,
                "niveau": niveau,
                "raisons": raisons,
            }
            if score >= AUTO_MERGE_THRESHOLD:
                high.append(pair)
            elif score >= CANDIDATE_THRESHOLD:
                medium.append(pair)
            elif score > 0:
                low.append(pair)

    # Statistiques place_id
    place_ids = [r.get("place_id_si_visible", "").strip() for r in rows if r.get("place_id_si_visible", "").strip()]
    unique_place_ids = len(set(place_ids))
    duplicate_place_ids = len(place_ids) - unique_place_ids

    report = {
        "generated_at": __import__('datetime').datetime.now().isoformat(timespec="seconds"),
        "total_analyzed": len(sample),
        "total_pairs_analyzed": len(sample) * (len(sample) - 1) // 2,
        "high_confidence_duplicates": len(high),
        "medium_confidence_candidates": len(medium),
        "low_confidence_matches": len(low),
        "high_pairs": high[:50],  # Limiter pour la taille du rapport
        "medium_pairs": medium[:50],
        "low_pairs": low[:50],
        "place_id_stats": {
            "total": len(place_ids),
            "unique": unique_place_ids,
            "duplicates": duplicate_place_ids,
            "coverage_pct": round(100.0 * len(place_ids) / len(rows), 2) if rows else 0.0,
        },
        "recommendation": (
            "Fusionner uniquement les HIGH. "
            "Vérifier manuellement les MEDIUM. "
            "Ignorer les LOW."
        ),
    }
    return report


def save_dedup_report(rows: List[dict], output_path: Path, sample_size: int = 500):
    report = generate_dedup_report(rows, sample_size)
    tmp = output_path.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(output_path)
    return report
