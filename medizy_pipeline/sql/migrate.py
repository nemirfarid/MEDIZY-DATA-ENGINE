#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Script de Migration et Initialisation Base de Données
========================================================================
Exécute le script DDL `001_facilities_and_suggestions_postgis.sql`, vérifie
l'activation des extensions PostGIS/unaccent/pg_trgm et valide les index GiST.
Supporte PostgreSQL (PostGIS) et SQLite (Local/Dev/Fallback).
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("medizy.migrate")

SQL_FILE_PATH = os.path.join(os.path.dirname(__file__), "001_facilities_and_suggestions_postgis.sql")


def run_postgres_migration(db_url: str) -> Dict[str, any]:
    """Exécute la migration complète sur PostgreSQL/PostGIS et valide les objets créés."""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        logger.error("Le package psycopg2 n'est pas disponible pour exécuter la migration PostgreSQL.")
        raise

    logger.info("Connexion à l'instance PostgreSQL...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    report = {
        "status": "pending",
        "extensions": [],
        "gist_indexes": [],
        "tables": [],
        "views": [],
        "functions": [],
    }

    try:
        # 1. Lecture et exécution du fichier SQL
        with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
            sql_script = f.read()

        logger.info(f"Application du script DDL PostGIS ({SQL_FILE_PATH})...")
        cursor.execute(sql_script)
        logger.info("Script SQL exécuté avec succès.")

        # 2. Vérification des extensions activées
        cursor.execute("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname IN ('postgis', 'unaccent', 'pg_trgm');
        """)
        extensions = cursor.fetchall()
        report["extensions"] = [{"name": row["extname"], "version": row["extversion"]} for row in extensions]
        ext_names = [e["name"] for e in report["extensions"]]
        logger.info(f"Extensions vérifiées : {', '.join(ext_names)}")

        # 3. Validation des index GiST sur les colonnes géométriques
        cursor.execute("""
            SELECT tablename, indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename IN ('facilities', 'facility_suggestions') 
              AND indexdef ILIKE '%gist%';
        """)
        gist_rows = cursor.fetchall()
        report["gist_indexes"] = [
            {"table": row["tablename"], "index": row["indexname"], "def": row["indexdef"]}
            for row in gist_rows
        ]
        for idx in report["gist_indexes"]:
            logger.info(f"Index spatial GiST validé : {idx['table']}.{idx['index']}")

        # 4. Vérification des tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('facilities', 'facility_suggestions');
        """)
        report["tables"] = [row["table_name"] for row in cursor.fetchall()]

        # 5. Vérification des vues
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
              AND table_name = 'v_facilities_public';
        """)
        report["views"] = [row["table_name"] for row in cursor.fetchall()]

        # 6. Vérification des fonctions
        cursor.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
              AND routine_name IN ('fn_approve_facility_suggestion', 'fn_sync_suggestion_geom', 'fn_update_timestamp');
        """)
        report["functions"] = [row["routine_name"] for row in cursor.fetchall()]

        report["status"] = "success"
        logger.info("Validation complète de la migration PostGIS réussie.")
        return report

    finally:
        cursor.close()
        conn.close()


def run_sqlite_migration(sqlite_path: str) -> Dict[str, any]:
    """Initialise le schéma local SQLite pour le développement ou mode offline."""
    import sqlite3
    logger.info(f"Initialisation du schéma local SQLite sur {sqlite_path}...")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS facilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            wilaya TEXT NOT NULL,
            wilaya_code TEXT,
            commune TEXT,
            address TEXT,
            phone TEXT,
            phone_normalized TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            is_claimed INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0,
            source TEXT DEFAULT 'manual',
            google_place_id TEXT UNIQUE,
            osm_id TEXT UNIQUE,
            metadata TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fac_wilaya ON facilities(wilaya)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fac_type ON facilities(type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fac_coords ON facilities(latitude, longitude)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fac_claimed ON facilities(is_claimed)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS facility_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT,
            wilaya TEXT NOT NULL,
            commune TEXT,
            address TEXT,
            phone TEXT,
            latitude REAL,
            longitude REAL,
            google_maps_url TEXT,
            submitter_name TEXT,
            submitter_email TEXT,
            submitter_phone TEXT,
            submitter_notes TEXT,
            status TEXT DEFAULT 'PENDING',
            matched_facility_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sug_status ON facility_suggestions(status)")

    conn.commit()
    conn.close()
    logger.info(f"Schéma SQLite initialisé avec succès sur {sqlite_path}.")
    return {"status": "success", "mode": "sqlite", "path": sqlite_path}


def get_default_sqlite_path() -> str:
    if os.environ.get("SQLITE_DB_PATH"):
        return os.environ["SQLITE_DB_PATH"]
    if os.path.exists("E:\\"):
        os.makedirs("E:\\medizy_data", exist_ok=True)
        return "E:\\medizy_data\\medizy_facilities_local.db"
    return "medizy_facilities_local.db"


def main():
    parser = argparse.ArgumentParser(description="Migration et initialisation de la base MEDIZY")
    parser.add_argument("--db-url", type=str, help="URL de connexion PostgreSQL (PostGIS)")
    parser.add_argument("--sqlite-path", type=str, default=get_default_sqlite_path(), help="Chemin fichier SQLite local")
    args = parser.parse_args()

    db_url = args.db_url or os.environ.get("DATABASE_URL")

    if db_url and db_url.startswith(("postgres://", "postgresql://")):
        logger.info(f"Mode cible : PostgreSQL / PostGIS ({db_url.split('@')[-1]})")
        try:
            report = run_postgres_migration(db_url)
            print("\n=== RAPPORT DE MIGRATION POSTGRESQL / POSTGIS ===")
            print(f"Statut       : {report['status'].upper()}")
            print(f"Extensions   : {[e['name'] + ' ' + e['version'] for e in report['extensions']]}")
            print(f"Index GiST   : {[i['table'] + '.' + i['index'] for i in report['gist_indexes']]}")
            print(f"Tables       : {report['tables']}")
            print(f"Vues         : {report['views']}")
            print(f"Fonctions    : {report['functions']}")
            print("===================================================\n")
        except Exception as e:
            logger.error(f"Échec de la migration PostgreSQL: {e}")
            sys.exit(1)
    else:
        logger.info("Aucune URL PostgreSQL fournie. Initialisation du mode SQLite de développement...")
        report = run_sqlite_migration(args.sqlite_path)
        print("\n=== RAPPORT INITIALISATION SQLITE (DEV/OFFLINE) ===")
        print(f"Statut : {report['status'].upper()}")
        print(f"Base   : {report['path']}")
        print("Note   : Pour cibler PostgreSQL, définir DATABASE_URL ou utiliser le flag --db-url.")
        print("===================================================\n")


if __name__ == "__main__":
    main()
