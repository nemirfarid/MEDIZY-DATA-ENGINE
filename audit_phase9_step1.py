#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SANTÉ DZ MEDIZY - PHASE 9 - ÉTAPE 1
Script d'audit en lecture seule de l'environnement de production.
Base: C:\\SANTE_DZ_SCRAPER\\medizy_scraper.db
"""

import hashlib
import os
import sqlite3
import sys

EXPECTED_SHA256 = "948fda84d6375b6b1dbd7ba822cdcfe09f7301f81f8779bc803e717b582c493d"
EXPECTED_TOTAL = 23669
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "medizy_scraper.db"))


def calculate_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()


def run_audit():
    print("=" * 70)
    print("SANTÉ DZ MEDIZY - AUDIT DE PRODUCTION PHASE 9 - ÉTAPE 1")
    print("=" * 70)
    print(f"Base de données : {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"ERREUR CRITIQUE : Base {DB_PATH} introuvable.")
        sys.exit(1)

    file_size = os.path.getsize(DB_PATH)
    print(f"Taille du fichier : {file_size:,} octets")

    actual_sha256 = calculate_sha256(DB_PATH)
    print(f"SHA-256 calculé   : {actual_sha256}")
    print(f"SHA-256 attendu   : {EXPECTED_SHA256}")

    if actual_sha256 == EXPECTED_SHA256:
        print("[SUCCÈS] SHA-256 CONFORME (correspond exactement à la fusion Phase 8.4)")
    else:
        print("[ATTENTION] Différence détectée sur le SHA-256 !")

    # Connexion en mode lecture seule stricte
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    cursor = conn.cursor()

    try:
        # 1. Intégrité SQLite
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchone()[0]
        print(f"PRAGMA integrity_check : {integrity}")

        # 2. Indexes sur la table places
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='places'")
        indexes = cursor.fetchall()
        print(f"\nIndexes sur 'places' ({len(indexes)}) :")
        for idx_name, idx_sql in indexes:
            print(f"  - {idx_name}: {idx_sql or '(auto-index)'}")

        # 3. Nombre total d'enregistrements
        cursor.execute("SELECT COUNT(*) FROM places;")
        total_places = cursor.fetchone()[0]
        print(f"\nNombre total d'établissements : {total_places:,} (attendu: {EXPECTED_TOTAL:,})")
        if total_places == EXPECTED_TOTAL:
            print("[SUCCÈS] Total d'enregistrements CONFORME (23 669)")

        # 4. Répartition par source
        print("\n" + "-" * 50)
        print("RÉPARTITION PAR SOURCE")
        print("-" * 50)
        cursor.execute("""
            SELECT 
                source,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / ?, 2) as pct
            FROM places
            GROUP BY source
            ORDER BY count DESC;
        """, (total_places,))
        sources_raw = cursor.fetchall()

        cursor.execute("""
            SELECT 
                CASE 
                    WHEN source LIKE 'osm_overpass%' THEN 'OpenStreetMap (Overpass)'
                    WHEN source LIKE 'geoalgeria%' THEN 'GeoAlgeria'
                    WHEN source = 'MIPH_2025' THEN 'MIPH 2025 (Ministère)'
                    WHEN source LIKE 'Google Maps%' THEN 'Google Maps public UI'
                    ELSE 'Autre / Inconnu'
                END as groupe_source,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / ?, 2) as pct
            FROM places
            GROUP BY groupe_source
            ORDER BY count DESC;
        """, (total_places,))
        sources_grouped = cursor.fetchall()

        for group_name, count, pct in sources_grouped:
            print(f"  * {group_name:<28} : {count:>6,} ({pct:>5.2f} %)")

        print("\nDétail fin par valeur de champ 'source' :")
        for src, count, pct in sources_raw:
            print(f"    - {src:<40} : {count:>6,} ({pct:>5.2f} %)")

        # 5. Couverture géographique et GPS
        print("\n" + "-" * 50)
        print("COUVERTURE GÉOGRAPHIQUE & GPS")
        print("-" * 50)
        cursor.execute("SELECT COUNT(DISTINCT wilaya) FROM places WHERE wilaya IS NOT NULL AND wilaya != '';")
        nb_wilayas = cursor.fetchone()[0]
        print(f"Nombre de wilayas couvertes     : {nb_wilayas}/58")

        cursor.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL;")
        nb_gps = cursor.fetchone()[0]
        print(f"Entrées avec coordonnées GPS    : {nb_gps:,}/{total_places:,} ({nb_gps * 100.0 / total_places:.2f} %)")

        cursor.execute("SELECT COUNT(*) FROM places WHERE commune IS NOT NULL AND TRIM(commune) != '';")
        nb_communes = cursor.fetchone()[0]
        print(f"Entrées avec commune renseignée : {nb_communes:,}/{total_places:,} ({nb_communes * 100.0 / total_places:.2f} %)")

        cursor.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND TRIM(telephone) != '';")
        nb_tel = cursor.fetchone()[0]
        print(f"Entrées avec téléphone          : {nb_tel:,}/{total_places:,} ({nb_tel * 100.0 / total_places:.2f} %)")

        # 6. Top 5 catégories médicales
        print("\n" + "-" * 50)
        print("TOP 10 CATÉGORIES / SPÉCIALITÉS MÉDICALES")
        print("-" * 50)
        cursor.execute("""
            SELECT categorie_recherche, COUNT(*) as cnt
            FROM places
            GROUP BY categorie_recherche
            ORDER BY cnt DESC
            LIMIT 10;
        """)
        for cat, cnt in cursor.fetchall():
            print(f"  * {cat:<32} : {cnt:>5,} entrées")

    finally:
        conn.close()

    print("\n" + "=" * 70)
    print("FIN DE L'AUDIT ÉTAPE 1")
    print("=" * 70)


if __name__ == "__main__":
    run_audit()
