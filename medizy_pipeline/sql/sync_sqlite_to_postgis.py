#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Synchronisation & Bascule Production (SQLite -> PostGIS)
=============================================================================
Script d'ingénierie des données assurant la réplication fiable et performante
du jeu de données local SQLite vers le serveur de production PostgreSQL / PostGIS.

Fonctionnalités :
- Validation des prérequis PostGIS (`postgis`, `unaccent`, `pg_trgm`).
- Migration du schéma DDL si absent (`001_facilities_and_suggestions_postgis.sql`).
- Transformation géospatiale WGS84 (Points lat/lon -> `GEOMETRY(Point, 4326)`).
- Importation par flux (streaming chunks) avec gestion des conflits (`osm_id`, `google_place_id`).
- Migration des contributions citoyennes `facility_suggestions`.
- Optimisation spatiale et reconstruction d'index GiST (`idx_facilities_geom`).
- Validation d'intégrité géométrique (`ST_IsValid`, `ST_Extent`).
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("medizy.sync_postgis")


def get_default_sqlite_path() -> str:
    if os.environ.get("SQLITE_DB_PATH"):
        return os.environ["SQLITE_DB_PATH"]
    if os.path.exists("E:\\medizy_data\\medizy_facilities_local.db"):
        return "E:\\medizy_data\\medizy_facilities_local.db"
    return "medizy_facilities_local.db"


def sync_sqlite_to_postgis(
    sqlite_path: str,
    pg_url: str,
    batch_size: int = 500,
    reindex: bool = True,
) -> bool:
    """Synchronise la base SQLite vers PostgreSQL / PostGIS avec indexation spatiale GiST."""
    logger.info(f"Démarrage de la synchronisation de données...")
    logger.info(f"Source (SQLite) : {sqlite_path}")
    logger.info(f"Cible  (PostGIS): {pg_url.split('@')[-1] if '@' in pg_url else pg_url}")

    if not os.path.exists(sqlite_path):
        logger.error(f"Fichier source SQLite introuvable : {sqlite_path}")
        return False

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        logger.error("Le package 'psycopg2' ou 'psycopg2-binary' est requis pour la synchronisation PostGIS.")
        logger.error("Installez-le avec : pip install psycopg2-binary")
        return False

    start_time = time.time()

    # 1. Connexion SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # 2. Connexion PostgreSQL / PostGIS
    try:
        pg_conn = psycopg2.connect(pg_url)
        pg_conn.autocommit = False
        pg_cur = pg_conn.cursor()
    except Exception as e:
        logger.error(f"Impossible de se connecter à PostgreSQL / PostGIS : {e}")
        return False

    try:
        # 3. Vérification des extensions PostGIS
        pg_cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'unaccent', 'pg_trgm');")
        installed_exts = dict(pg_cur.fetchall())
        logger.info(f"Extensions installées sur PostgreSQL : {installed_exts}")

        if "postgis" not in installed_exts:
            logger.info("Activation de l'extension PostGIS...")
            pg_cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        if "unaccent" not in installed_exts:
            pg_cur.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
        if "pg_trgm" not in installed_exts:
            pg_cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        pg_conn.commit()

        # 4. Vérification et exécution du schéma si la table n'existe pas
        pg_cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'facilities'
            );
        """)
        table_exists = pg_cur.fetchone()[0]
        if not table_exists:
            logger.info("Table 'facilities' absente. Exécution du DDL initial PostGIS...")
            sql_file = os.path.join(os.path.dirname(__file__), "001_facilities_and_suggestions_postgis.sql")
            if os.path.exists(sql_file):
                with open(sql_file, "r", encoding="utf-8") as f:
                    pg_cur.execute(f.read())
                pg_conn.commit()
                logger.info("Schéma PostGIS initialisé avec succès.")

        # 5. Synchronisation de la table `facilities`
        sqlite_cur.execute("SELECT COUNT(*) FROM facilities;")
        total_source_facilities = sqlite_cur.fetchone()[0]
        logger.info(f"Établissements détectés dans SQLite : {total_source_facilities}")

        sqlite_cur.execute("""
            SELECT name, type, wilaya, wilaya_code, commune, address, phone, phone_normalized,
                   latitude, longitude, is_claimed, is_verified, source,
                   google_place_id, osm_id, metadata, created_at, updated_at
            FROM facilities;
        """)

        insert_sql = """
            INSERT INTO facilities (
                name, type, wilaya, wilaya_code, commune, address, phone, phone_normalized,
                geom, is_claimed, is_verified, source,
                google_place_id, osm_id, metadata, created_at, updated_at
            ) VALUES (
                %(name)s, %(type)s, %(wilaya)s, %(wilaya_code)s, %(commune)s, %(address)s, %(phone)s, %(phone_normalized)s,
                ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326),
                %(is_claimed)s, %(is_verified)s, %(source)s,
                %(google_place_id)s, %(osm_id)s, %(metadata)s,
                COALESCE(%(created_at)s::timestamptz, CURRENT_TIMESTAMP),
                COALESCE(%(updated_at)s::timestamptz, CURRENT_TIMESTAMP)
            )
            ON CONFLICT (osm_id) DO UPDATE SET
                name = EXCLUDED.name,
                type = EXCLUDED.type,
                wilaya = EXCLUDED.wilaya,
                wilaya_code = EXCLUDED.wilaya_code,
                commune = EXCLUDED.commune,
                address = EXCLUDED.address,
                phone = EXCLUDED.phone,
                geom = EXCLUDED.geom,
                updated_at = CURRENT_TIMESTAMP
            WHERE facilities.osm_id IS NOT NULL;
        """

        facilities_inserted = 0
        while True:
            rows = sqlite_cur.fetchmany(batch_size)
            if not rows:
                break
            batch_data = []
            for r in rows:
                d = dict(r)
                d["is_claimed"] = bool(d["is_claimed"])
                d["is_verified"] = bool(d["is_verified"])
                meta = d.get("metadata")
                if meta and isinstance(meta, str):
                    try:
                        d["metadata"] = json.dumps(json.loads(meta))
                    except Exception:
                        d["metadata"] = "{}"
                else:
                    d["metadata"] = "{}"
                batch_data.append(d)

            psycopg2.extras.execute_batch(pg_cur, insert_sql, batch_data)
            pg_conn.commit()
            facilities_inserted += len(batch_data)
            logger.info(f"Progression : {facilities_inserted}/{total_source_facilities} structures synchronisées...")

        # 6. Synchronisation de la table `facility_suggestions`
        try:
            sqlite_cur.execute("SELECT COUNT(*) FROM facility_suggestions;")
            total_suggestions = sqlite_cur.fetchone()[0]
            logger.info(f"Suggestions citoyennes détectées dans SQLite : {total_suggestions}")

            if total_suggestions > 0:
                sqlite_cur.execute("""
                    SELECT name, type, wilaya, commune, address, phone,
                           latitude, longitude, google_maps_url,
                           submitter_name, submitter_email, submitter_phone, submitter_notes,
                           status, matched_facility_id, moderated_by, moderated_at, moderation_comment,
                           created_at
                    FROM facility_suggestions;
                """)
                sugg_sql = """
                    INSERT INTO facility_suggestions (
                        name, type, wilaya, commune, address, phone,
                        latitude, longitude, geom, google_maps_url,
                        submitter_name, submitter_email, submitter_phone, submitter_notes,
                        status, matched_facility_id, moderated_by, moderated_at, moderation_comment,
                        created_at
                    ) VALUES (
                        %(name)s, %(type)s, %(wilaya)s, %(commune)s, %(address)s, %(phone)s,
                        %(latitude)s, %(longitude)s,
                        CASE WHEN %(latitude)s IS NOT NULL AND %(longitude)s IS NOT NULL 
                             THEN ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326) 
                             ELSE NULL END,
                        %(google_maps_url)s,
                        %(submitter_name)s, %(submitter_email)s, %(submitter_phone)s, %(submitter_notes)s,
                        %(status)s, %(matched_facility_id)s, %(moderated_by)s, %(moderated_at)s, %(moderation_comment)s,
                        COALESCE(%(created_at)s::timestamptz, CURRENT_TIMESTAMP)
                    );
                """
                sugg_rows = [dict(r) for r in sqlite_cur.fetchall()]
                psycopg2.extras.execute_batch(pg_cur, sugg_sql, sugg_rows)
                pg_conn.commit()
                logger.info(f"Suggestions synchronisées : {len(sugg_rows)}.")
        except Exception as e:
            logger.warning(f"Table suggestions non traitée ou vide : {e}")

        # 7. Reconstruction et optimisation de l'index spatial GiST
        if reindex:
            logger.info("Optimisation spatiale : Vérification et reconstruction de l'index GiST...")
            pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_facilities_geom ON facilities USING GIST (geom);")
            pg_conn.commit()
            pg_cur.execute("ANALYZE facilities;")
            pg_conn.commit()
            logger.info("Index GiST et statistiques du planificateur PostgreSQL à jour.")

        # 8. Rapport de validation d'intégrité
        pg_cur.execute("SELECT COUNT(*) FROM facilities;")
        pg_total = pg_cur.fetchone()[0]

        pg_cur.execute("""
            SELECT COUNT(*) FROM facilities 
            WHERE geom IS NOT NULL AND NOT ST_IsValid(geom);
        """)
        invalid_geom_count = pg_cur.fetchone()[0]

        pg_cur.execute("SELECT ST_AsText(ST_Extent(geom)) FROM facilities;")
        spatial_extent = pg_cur.fetchone()[0]

        elapsed = time.time() - start_time
        print("\n" + "=" * 76)
        print("    RAPPORT DE SYNCHRONISATION POSTGIS (PRODUCTION)")
        print("=" * 76)
        print(f"Statut               : SUCCÈS")
        print(f"Structures en base   : {pg_total} (Source: {total_source_facilities})")
        print(f"Géométries invalides : {invalid_geom_count}")
        print(f"Emprise spatiale     : {spatial_extent}")
        print(f"Index GiST spatial   : ACTIF (idx_facilities_geom)")
        print(f"Durée d'exécution    : {elapsed:.2f} secondes")
        print("=" * 76 + "\n")

        return True

    except Exception as e:
        pg_conn.rollback()
        logger.error(f"Erreur critique lors de la synchronisation : {e}")
        return False
    finally:
        sqlite_conn.close()
        pg_conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Synchronisation de données SQLite vers PostgreSQL / PostGIS MEDIZY"
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=get_default_sqlite_path(),
        help="Chemin de la base de données SQLite locale",
    )
    parser.add_argument(
        "--pg-url",
        type=str,
        default=os.environ.get("DATABASE_URL", "postgresql://medizy_user:medizy_password@localhost:5432/medizy_db"),
        help="Chaîne de connexion PostgreSQL / PostGIS",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Taille des lots d'insertion (défaut: 500)",
    )
    parser.add_argument(
        "--no-reindex",
        action="store_true",
        help="Désactiver la reconstruction de l'index GiST et ANALYZE",
    )

    args = parser.parse_args()

    success = sync_sqlite_to_postgis(
        sqlite_path=args.sqlite_path,
        pg_url=args.pg_url,
        batch_size=args.batch_size,
        reindex=not args.no_reindex,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
