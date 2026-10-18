#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SANTÉ DZ / MEDIZY — CONSTRUCTEUR ET DÉPLOIEMENT DU BUNDLE EMBARQUÉ CLIENT (PHASE 9)
===================================================================================
1. Copie medizy_national_cache.json.gz vers sante_dz_db.json.gz
2. Déploie les index wilayas et catégories dans les assets
3. Génère la base SQLite mobile haute performance sante_dz_bundled.db avec :
   - Table relationnelle 'facilities'
   - Moteur FTS5 (Full-Text Search) sur nom, commune, wilaya, categorie
   - Index spatial R-Tree sur coordonnées géographiques (lat, lon)
   - Index B-Tree standards optimisés pour les requêtes hors-ligne
"""

import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from export_mobile_cache import OFFICIAL_WILAYAS, calculate_sha256

SOURCE_DB = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
MOBILE_DIR = r"D:\SANTE_DZ_EXPORTS\mobile"
ASSETS_DIR = r"D:\SANTE_DZ_EXPORTS\mobile\assets\data"
EXPECTED_COUNT = 35832


def deploy_bundled_assets():
    print("=" * 75)
    print("SANTÉ DZ / MEDIZY — CONSTITUTION DU BUNDLE ASSETS APPLICATION MOBILE")
    print("=" * 75)
    print(f"Base de production source : {SOURCE_DB}")
    print(f"Répertoire mobile         : {MOBILE_DIR}")
    print(f"Répertoire assets cible   : {ASSETS_DIR}")

    os.makedirs(MOBILE_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # 1. Déploiement de sante_dz_db.json.gz
    src_gz = os.path.join(MOBILE_DIR, "medizy_national_cache.json.gz")
    if not os.path.exists(src_gz):
        raise FileNotFoundError(f"Cache national source introuvable à {src_gz}")

    target_gz_assets = os.path.join(ASSETS_DIR, "sante_dz_db.json.gz")
    target_gz_root = os.path.join(MOBILE_DIR, "sante_dz_db.json.gz")
    shutil.copyfile(src_gz, target_gz_assets)
    shutil.copyfile(src_gz, target_gz_root)
    gz_size = os.path.getsize(target_gz_assets)
    print(f"[1/4] Bundle JSON.GZ déployé : {target_gz_assets} ({gz_size / (1024*1024):.2f} MB)")

    # 2. Déploiement des index JSON
    for index_name in ["medizy_wilayas_index.json", "medizy_categories_index.json"]:
        src_idx = os.path.join(MOBILE_DIR, index_name)
        if os.path.exists(src_idx):
            dst_idx = os.path.join(ASSETS_DIR, index_name)
            shutil.copyfile(src_idx, dst_idx)
            print(f"[2/4] Index déployé dans assets : {dst_idx}")

    # 3. Construction de la base SQLite embarquée sante_dz_bundled.db
    target_db_path = os.path.join(MOBILE_DIR, "sante_dz_bundled.db")
    if os.path.exists(target_db_path):
        os.remove(target_db_path)

    print(f"\n[3/4] Création et indexation SQLite FTS5 + R-Tree : {target_db_path}...")
    t0_db = time.perf_counter()

    # Connexion à la base cible
    conn_target = sqlite3.connect(target_db_path)
    cur_target = conn_target.cursor()

    cur_target.execute("PRAGMA journal_mode = OFF;")
    cur_target.execute("PRAGMA synchronous = OFF;")
    cur_target.execute("PRAGMA page_size = 4096;")

    # Création table relationnelle
    cur_target.execute("""
        CREATE TABLE facilities (
            id INTEGER PRIMARY KEY,
            place_id TEXT,
            nom TEXT NOT NULL,
            categorie TEXT NOT NULL,
            wilaya TEXT NOT NULL,
            wilaya_code TEXT NOT NULL,
            commune TEXT NOT NULL,
            adresse TEXT,
            telephone TEXT,
            site_web TEXT,
            note REAL,
            nombre_avis INTEGER,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            source TEXT
        );
    """)

    # Création table FTS5 avec colonnes directes pour accès instantané sans JOIN (< 1 ms)
    cur_target.execute("""
        CREATE VIRTUAL TABLE facilities_fts USING fts5(
            nom,
            commune,
            wilaya,
            categorie,
            telephone UNINDEXED,
            latitude UNINDEXED,
            longitude UNINDEXED,
            content='facilities',
            content_rowid='id'
        );
    """)

    # Création table R-Tree
    cur_target.execute("""
        CREATE VIRTUAL TABLE facilities_rtree USING rtree(
            id,
            min_lat, max_lat,
            min_lon, max_lon
        );
    """)

    # Connexion source en lecture seule
    conn_src = sqlite3.connect(f"file:{SOURCE_DB}?mode=ro", uri=True)
    conn_src.row_factory = sqlite3.Row
    cur_src = conn_src.cursor()

    wilaya_to_code = {name.lower(): code for code, name in OFFICIAL_WILAYAS}
    wilaya_to_code["el m'ghair"] = "57"
    wilaya_to_code["el meghaier"] = "57"
    wilaya_to_code["el mghair"] = "57"

    cur_src.execute("""
        SELECT 
            id, place_id, nom, categorie_recherche, wilaya, commune,
            adresse, telephone, site_web, note, nombre_avis,
            latitude, longitude, source
        FROM places
        ORDER BY id ASC;
    """)
    rows = cur_src.fetchall()
    conn_src.close()

    insert_rows = []
    fts_rows = []
    rtree_rows = []

    for r in rows:
        w_name = r["wilaya"] or "Inconnue"
        w_code = wilaya_to_code.get(w_name.lower(), "99")
        lat = float(r["latitude"]) if r["latitude"] is not None else 0.0
        lon = float(r["longitude"]) if r["longitude"] is not None else 0.0
        cat = r["categorie_recherche"] or "autre"
        nom = r["nom"] or ""
        com = r["commune"] or ""

        insert_rows.append((
            r["id"],
            r["place_id"] or "",
            nom,
            cat,
            w_name,
            w_code,
            com,
            r["adresse"] or "",
            r["telephone"] or "",
            r["site_web"] or "",
            r["note"],
            r["nombre_avis"],
            lat,
            lon,
            r["source"] or "medizy_official_db"
        ))

        fts_rows.append((r["id"], nom, com, w_name, cat, r["telephone"] or "", lat, lon))
        rtree_rows.append((r["id"], lat, lat, lon, lon))

    # Insertion en bloc
    cur_target.executemany("""
        INSERT INTO facilities (
            id, place_id, nom, categorie, wilaya, wilaya_code, commune,
            adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, insert_rows)

    cur_target.executemany("""
        INSERT INTO facilities_fts (rowid, nom, commune, wilaya, categorie, telephone, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, fts_rows)

    cur_target.executemany("""
        INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
        VALUES (?, ?, ?, ?, ?);
    """, rtree_rows)

    # Index standards pour les clauses WHERE / ORDER BY rapides
    cur_target.execute("CREATE INDEX idx_facilities_wilaya ON facilities(wilaya);")
    cur_target.execute("CREATE INDEX idx_facilities_wilaya_code ON facilities(wilaya_code);")
    cur_target.execute("CREATE INDEX idx_facilities_commune ON facilities(commune);")
    cur_target.execute("CREATE INDEX idx_facilities_categorie ON facilities(categorie);")
    cur_target.execute("CREATE INDEX idx_facilities_coords ON facilities(latitude, longitude);")

    cur_target.execute("PRAGMA user_version = 15;")
    conn_target.commit()

    # Optimisation finale de l'espace disque
    cur_target.execute("VACUUM;")
    conn_target.close()

    # Re-vérification avec contrôles stricts
    conn_check = sqlite3.connect(f"file:{target_db_path}?mode=ro", uri=True)
    cur_check = conn_check.cursor()
    cur_check.execute("PRAGMA integrity_check;")
    integ = cur_check.fetchone()[0]
    assert integ == "ok", f"Intégrité compromise sur bundle : {integ}"

    cur_check.execute("SELECT COUNT(*) FROM facilities;")
    count_fac = cur_check.fetchone()[0]
    assert count_fac == EXPECTED_COUNT, f"Volume facilities {count_fac} != {EXPECTED_COUNT}"

    cur_check.execute("SELECT COUNT(*) FROM facilities_fts;")
    count_fts = cur_check.fetchone()[0]
    assert count_fts == EXPECTED_COUNT, f"Volume fts {count_fts} != {EXPECTED_COUNT}"

    cur_check.execute("SELECT COUNT(*) FROM facilities_rtree;")
    count_rtree = cur_check.fetchone()[0]
    assert count_rtree == EXPECTED_COUNT, f"Volume rtree {count_rtree} != {EXPECTED_COUNT}"

    conn_check.close()

    # Copier la base dans le dossier assets également
    target_db_assets = os.path.join(ASSETS_DIR, "sante_dz_bundled.db")
    shutil.copyfile(target_db_path, target_db_assets)

    t1_db = time.perf_counter()
    db_size = os.path.getsize(target_db_path)
    print(f"[4/4] Base SQLite FTS5/R-Tree générée : {target_db_path}")
    print(f"      * Taille bundle           : {db_size / (1024*1024):.2f} MB")
    print(f"      * Fiches indexées         : {count_fac:,} (100% conformes)")
    print(f"      * FTS5 index              : {count_fts:,} fiches indexées plein texte")
    print(f"      * R-Tree spatial index    : {count_rtree:,} coordonnées indexées")
    print(f"      * Copie assets            : {target_db_assets}")
    print(f"      * Durée de construction   : {round(t1_db - t0_db, 2)} s")

    print("\n" + "=" * 75)
    print("[SUCCÈS] Tous les artefacts client sont déployés et prêts pour intégration.")
    print("=" * 75)


if __name__ == "__main__":
    deploy_bundled_assets()
