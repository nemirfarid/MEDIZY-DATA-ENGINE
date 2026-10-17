#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Surveillance & Validation d'Intégrité du Cache Mobile (Phase 5)
===================================================================================
Vérifie la conformité, l'intégrité de décompression et la concordance
cryptographique de l'archive nationale compressée GZIP (exports/mobile/medizy_national_cache.json.gz).
"""

import argparse
import gzip
import hashlib
import json
import os
import sys
import sqlite3
from typing import Any, Dict, Optional

DEFAULT_CACHE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "exports", "mobile", "medizy_national_cache.json.gz")
)
DEFAULT_DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "medizy_scraper.db")
)
EXPECTED_FACILITIES_COUNT = 30568
EXPECTED_WILAYAS_COUNT = 58


def compute_sha256(filepath: str) -> str:
    """Calcule la somme de contrôle SHA-256 d'un fichier."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def verify_cache(
    cache_path: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Exécute les contrôles d'intégrité sur l'archive GZIP nationale.
    Retourne un dictionnaire avec le statut détaillé.
    """
    c_path = os.path.abspath(cache_path or DEFAULT_CACHE_PATH)
    d_path = os.path.abspath(db_path or DEFAULT_DB_PATH)

    # 1. Vérification de l'existence des fichiers
    if not os.path.exists(c_path):
        raise FileNotFoundError(f"Archive de cache introuvable : {c_path}")
    if not os.path.exists(d_path):
        raise FileNotFoundError(f"Base de données de référence introuvable : {d_path}")

    cache_size_bytes = os.path.getsize(c_path)
    cache_sha256 = compute_sha256(c_path)
    db_sha256 = compute_sha256(d_path)

    # Récupération du volume réel de la base
    con = sqlite3.connect(f"file:{d_path}?mode=ro", uri=True)
    actual_db_count = con.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    con.close()

    # 2. Décompression en mémoire et validation JSON
    with gzip.open(c_path, "rt", encoding="utf-8") as f:
        cache_data = json.load(f)

    if not isinstance(cache_data, dict):
        raise ValueError("Format JSON invalide : la racine doit être un objet JSON.")

    if "metadata" not in cache_data or "facilities" not in cache_data:
        raise ValueError("Schéma invalide : clés 'metadata' et 'facilities' requises.")

    metadata = cache_data["metadata"]
    facilities = cache_data["facilities"]

    facilities_count = len(facilities)
    meta_count = metadata.get("total_facilities")
    meta_db_sha = metadata.get("source_db_sha256")
    meta_wilayas_count = metadata.get("wilayas_count")

    # 3. Contrôles de concordance stricte
    target_count = actual_db_count if actual_db_count > 0 else EXPECTED_FACILITIES_COUNT
    count_concordance = (facilities_count == target_count) and (meta_count == target_count)
    sha_concordance = (meta_db_sha == db_sha256)
    wilayas_concordance = (meta_wilayas_count == EXPECTED_WILAYAS_COUNT)

    # 4. Validation structurelle sur un échantillon d'établissements
    sample_valid = True
    required_keys = {"id", "nom", "cat", "wil", "lat", "lon"}
    for item in facilities[:100]:
        if not required_keys.issubset(item.keys()):
            sample_valid = False
            break

    is_valid = count_concordance and sha_concordance and wilayas_concordance and sample_valid

    report = {
        "status": "success" if is_valid else "failure",
        "cache_file": {
            "path": c_path,
            "size_bytes": cache_size_bytes,
            "size_human": f"{cache_size_bytes / (1024*1024):.2f} MB",
            "sha256": cache_sha256
        },
        "database_reference": {
            "path": d_path,
            "sha256": db_sha256
        },
        "validation_checks": {
            "facilities_count": facilities_count,
            "expected_count": EXPECTED_FACILITIES_COUNT,
            "count_concordance": count_concordance,
            "source_db_sha256_in_metadata": meta_db_sha,
            "actual_db_sha256": db_sha256,
            "sha_concordance": sha_concordance,
            "wilayas_count": meta_wilayas_count,
            "wilayas_concordance": wilayas_concordance,
            "schema_sample_valid": sample_valid
        },
        "overall_integrity": "CONFORME" if is_valid else "NON_CONFORME"
    }

    if not is_valid:
        raise ValueError(f"Échec de validation de l'archive de cache : {report['validation_checks']}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Vérificateur d'intégrité du cache de distribution Santé DZ Medizy")
    parser.add_argument("--cache-path", default=None, help="Chemin du fichier medizy_national_cache.json.gz")
    parser.add_argument("--db-path", default=None, help="Chemin de la base medizy_scraper.db")
    args = parser.parse_args()

    try:
        report = verify_cache(cache_path=args.cache_path, db_path=args.db_path)
        print("=" * 70)
        print("SANTÉ DZ MEDIZY — AUDIT DE CONFORMITÉ DU CACHE MOBILE")
        print("=" * 70)
        print(f"Archive testée     : {report['cache_file']['path']}")
        print(f"Taille compressée  : {report['cache_file']['size_human']} ({report['cache_file']['size_bytes']} octets)")
        print(f"SHA-256 Archive    : {report['cache_file']['sha256']}")
        print(f"Établissements     : {report['validation_checks']['facilities_count']:,} (attendu: {EXPECTED_FACILITIES_COUNT:,})")
        print(f"Couverture         : {report['validation_checks']['wilayas_count']} wilayas")
        print(f"Concordance SHA DB : {'OUI (Valide)' if report['validation_checks']['sha_concordance'] else 'NON'}")
        print(f"Résultat Global    : {report['overall_integrity']}")
        print("=" * 70)
        sys.exit(0)
    except Exception as e:
        print(f"[ERREUR] Échec de l'audit de cache : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
