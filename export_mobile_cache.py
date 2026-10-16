#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Export de Cache Hors-Ligne Mobile (Phase 10)
===============================================================
Génère des archives JSON compressées en GZIP (.json.gz) optimisées pour
alimenter le cache local hors-ligne de l'application cliente mobile.

Modes de fonctionnement :
-------------------------
1. Export par wilaya :
    python export_mobile_cache.py --wilaya 16
    Génère exports/mobile/medizy_wilaya_16_alger.json.gz

2. Export des 58 wilayas individuellement (découpage régional) :
    python export_mobile_cache.py --all-wilayas
    Génère 58 archives compressées dans exports/mobile/wilayas/

3. Export national complet consolidé :
    python export_mobile_cache.py --national
    Génère exports/mobile/medizy_national_cache.json.gz (23 669 entrées)

Sécurité :
----------
- Connexion en lecture seule stricte (mode=ro, uri=True).
- Contrôle d'intégrité par lecture/décompression immédiate après génération.
- Zero dépendance externe (gzip, json, sqlite3 natifs).
"""

import argparse
import datetime
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from medizy_search import MedizySearchEngine, OFFICIAL_WILAYAS, WILAYA_BY_CODE, strip_accents

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "medizy_scraper.db"))
EXPECTED_SHA256 = "948fda84d6375b6b1dbd7ba822cdcfe09f7301f81f8779bc803e717b582c493d"
DEFAULT_OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "exports", "mobile"))


def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def get_readonly_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def export_records_to_gzip(
    records: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    output_filepath: str
) -> Dict[str, Any]:
    """Écrit le dictionnaire consolidé dans une archive .json.gz avec compression niveau 9."""
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    
    payload = {
        "metadata": metadata,
        "facilities": records
    }
    
    raw_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    raw_size = len(raw_json.encode('utf-8'))

    t0 = time.perf_counter()
    with gzip.open(output_filepath, "wt", encoding="utf-8", compresslevel=9) as gz_out:
        gz_out.write(raw_json)
    t1 = time.perf_counter()

    compressed_size = os.path.getsize(output_filepath)
    ratio = (1.0 - (compressed_size / raw_size)) * 100.0 if raw_size > 0 else 0.0

    # Auto-vérification immédiate de décompression
    with gzip.open(output_filepath, "rt", encoding="utf-8") as gz_in:
        read_back = json.load(gz_in)
        assert len(read_back["facilities"]) == len(records), "Erreur d'intégrité lors de la relecture GZIP !"

    return {
        "filepath": output_filepath,
        "records_count": len(records),
        "raw_bytes": raw_size,
        "compressed_bytes": compressed_size,
        "compression_ratio_pct": round(ratio, 2),
        "write_time_ms": round((t1 - t0) * 1000.0, 2)
    }


def export_wilaya(
    wilaya_input: str,
    output_dir: str = DEFAULT_OUT_DIR,
    db_sha: str = ""
) -> Dict[str, Any]:
    """Exporte une wilaya spécifique sous forme de cache mobile GZIP."""
    engine = MedizySearchEngine(db_path=DB_PATH)
    resolved_name = engine.resolve_wilaya(wilaya_input)

    # Récupération et validation du code officiel
    wilaya_code = None
    for code, name in OFFICIAL_WILAYAS:
        if name.lower() == str(resolved_name).lower():
            wilaya_code = code
            resolved_name = name
            break

    if not wilaya_code:
        raise ValueError(f"Wilaya officielle introuvable ou non reconnue : {wilaya_input}")

    conn = get_readonly_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id, place_id, nom, categorie_recherche, wilaya, commune,
            adresse, telephone, site_web, note, nombre_avis,
            latitude, longitude, source
        FROM places
        WHERE wilaya = ?
        ORDER BY commune ASC, nom ASC
    """, (resolved_name,))
    rows = cur.fetchall()
    conn.close()

    records = []
    lats = []
    lons = []
    cat_counts = {}

    for r in rows:
        rec = {
            "id": r["id"],
            "pid": r["place_id"],
            "nom": r["nom"],
            "cat": r["categorie_recherche"],
            "wil": r["wilaya"],
            "com": r["commune"],
            "adr": r["adresse"],
            "tel": r["telephone"],
            "site": r["site_web"],
            "note": r["note"],
            "avis": r["nombre_avis"],
            "lat": r["latitude"],
            "lon": r["longitude"],
            "src": r["source"]
        }
        records.append(rec)
        if r["latitude"] is not None and r["longitude"] is not None:
            lats.append(r["latitude"])
            lons.append(r["longitude"])
        cat = r["categorie_recherche"] or "autre"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    bbox = {
        "min_lat": min(lats) if lats else None,
        "max_lat": max(lats) if lats else None,
        "min_lon": min(lons) if lons else None,
        "max_lon": max(lons) if lons else None,
    }

    norm_clean = strip_accents(resolved_name).replace(" ", "_").replace("'", "")
    filename = f"medizy_wilaya_{wilaya_code}_{norm_clean}.json.gz"
    output_path = os.path.join(output_dir, filename)

    metadata = {
        "version": "1.0.9",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "wilaya_code": wilaya_code,
        "wilaya": resolved_name,
        "total_facilities": len(records),
        "source_db_sha256": db_sha or calculate_sha256(DB_PATH),
        "bounding_box": bbox,
        "categories_summary": cat_counts
    }

    return export_records_to_gzip(records, metadata, output_path)


def export_all_wilayas_individual(output_dir: str = DEFAULT_OUT_DIR) -> List[Dict[str, Any]]:
    """Génère 58 archives GZIP individuelles pour chaque wilaya."""
    target_dir = os.path.join(output_dir, "wilayas")
    db_sha = calculate_sha256(DB_PATH)
    results = []
    print(f"Export des 58 wilayas individuelles vers {target_dir}...")
    
    total_raw = 0
    total_comp = 0
    total_recs = 0
    
    for code, name in OFFICIAL_WILAYAS:
        stat = export_wilaya(name, output_dir=target_dir, db_sha=db_sha)
        results.append(stat)
        total_raw += stat["raw_bytes"]
        total_comp += stat["compressed_bytes"]
        total_recs += stat["records_count"]
        print(f"  [{code}] {name:<22} : {stat['records_count']:>4} fiches | {stat['raw_bytes']/1024:>6.1f} KB -> {stat['compressed_bytes']/1024:>5.1f} KB GZ (-{stat['compression_ratio_pct']}%)")

    overall_ratio = (1.0 - (total_comp / total_raw)) * 100.0 if total_raw > 0 else 0
    print("-" * 70)
    print(f"TOTAL 58 WILAYAS : {total_recs:,} établissements exportés")
    print(f"Taille brute : {total_raw / (1024*1024):.2f} MB | Taille compressée : {total_comp / (1024*1024):.2f} MB (Gain global : {overall_ratio:.1f}%)")
    return results


def export_national_cache(output_dir: str = DEFAULT_OUT_DIR) -> Dict[str, Any]:
    """Exporte l'intégralité des 23 669 établissements en un seul package compressé."""
    db_sha = calculate_sha256(DB_PATH)
    conn = get_readonly_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            id, place_id, nom, categorie_recherche, wilaya, commune,
            adresse, telephone, site_web, note, nombre_avis,
            latitude, longitude, source
        FROM places
        ORDER BY wilaya ASC, commune ASC, nom ASC
    """)
    rows = cur.fetchall()
    conn.close()

    records = []
    lats = []
    lons = []
    wilaya_counts = {}
    cat_counts = {}

    for r in rows:
        rec = {
            "id": r["id"],
            "pid": r["place_id"],
            "nom": r["nom"],
            "cat": r["categorie_recherche"],
            "wil": r["wilaya"],
            "com": r["commune"],
            "adr": r["adresse"],
            "tel": r["telephone"],
            "site": r["site_web"],
            "note": r["note"],
            "avis": r["nombre_avis"],
            "lat": r["latitude"],
            "lon": r["longitude"],
            "src": r["source"]
        }
        records.append(rec)
        if r["latitude"] is not None and r["longitude"] is not None:
            lats.append(r["latitude"])
            lons.append(r["longitude"])
        w = r["wilaya"] or "Inconnue"
        wilaya_counts[w] = wilaya_counts.get(w, 0) + 1
        c = r["categorie_recherche"] or "autre"
        cat_counts[c] = cat_counts.get(c, 0) + 1

    bbox = {
        "min_lat": min(lats) if lats else None,
        "max_lat": max(lats) if lats else None,
        "min_lon": min(lons) if lons else None,
        "max_lon": max(lons) if lons else None,
    }

    output_path = os.path.join(output_dir, "medizy_national_cache.json.gz")
    metadata = {
        "version": "1.0.9",
        "package_type": "national_consolidated",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_facilities": len(records),
        "source_db_sha256": db_sha,
        "wilayas_count": len(wilaya_counts),
        "bounding_box": bbox,
        "wilayas_summary": wilaya_counts,
        "categories_summary": cat_counts
    }

    stat = export_records_to_gzip(records, metadata, output_path)
    print("\n" + "=" * 70)
    print("PACKAGE NATIONAL EXPORTÉ")
    print("=" * 70)
    print(f"Fichier            : {stat['filepath']}")
    print(f"Établissements     : {stat['records_count']:,}")
    print(f"Taille brute JSON  : {stat['raw_bytes'] / (1024*1024):.2f} MB")
    print(f"Taille GZIP        : {stat['compressed_bytes'] / (1024*1024):.2f} MB (-{stat['compression_ratio_pct']} %)")
    print(f"Temps d'écriture   : {stat['write_time_ms']} ms")
    return stat


def main():
    parser = argparse.ArgumentParser(description="Export compressé pour cache mobile Santé DZ Medizy")
    parser.add_argument("--wilaya", help="Nom ou code de wilaya à exporter (ex: 16 ou Alger)")
    parser.add_argument("--all-wilayas", action="store_true", help="Générer 58 fichiers distincts pour chaque wilaya")
    parser.add_argument("--national", action="store_true", help="Générer l'archive nationale consolidée complète")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Répertoire de destination")

    args = parser.parse_args()

    # Si aucun argument n'est fourni, exécuter les exports par défaut (wilaya 16 + national)
    if not args.wilaya and not args.all_wilayas and not args.national:
        print("Aucun mode spécifié. Exécution par défaut : export Wilaya 16 (Alger) et Package National.")
        stat_w = export_wilaya("16", output_dir=args.out_dir)
        print(f"[Wilaya 16] Généré : {stat_w['filepath']} ({stat_w['compressed_bytes']/1024:.1f} KB)")
        stat_nat = export_national_cache(output_dir=args.out_dir)
        return

    if args.wilaya:
        stat = export_wilaya(args.wilaya, output_dir=args.out_dir)
        print(f"Export terminé : {stat['filepath']}")
        print(f"Établissements : {stat['records_count']} | GZIP : {stat['compressed_bytes']/1024:.1f} KB (-{stat['compression_ratio_pct']}%)")

    if args.all_wilayas:
        export_all_wilayas_individual(output_dir=args.out_dir)

    if args.national:
        export_national_cache(output_dir=args.out_dir)


if __name__ == "__main__":
    main()
