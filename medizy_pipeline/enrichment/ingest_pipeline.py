#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Pipeline d'Ingestion & d'Enrichissement Automatique
=======================================================================
Orchestrateur national pour intégrer tous les établissements de santé manquants
(hôpitaux, polycliniques, cliniques, EPSP, EPH, CHU) sur les 58 wilayas.

Fonctionnalités :
  - Découpage par wilaya avec coordonnées et bounding boxes
  - Collecte OSM Overpass et/ou Google Places
  - Déduplication stricte (< 100m géospatial + matching textuel)
  - Insertion avec `is_claimed = false` et `is_verified = false`
  - Rapports d'ingestion détaillés par wilaya et nationaux
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .classifier import classify_facility, normalize_algerian_phone
from .deduplication import is_duplicate_match
from .google_places import GooglePlacesClient
from .osm_overpass import OverpassClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("medizy.pipeline")

# Référentiel des 58 Wilayas d'Algérie avec Bounding Box approximative (min_lat, min_lon, max_lat, max_lon)
ALGERIAN_WILAYAS: List[Dict[str, Any]] = [
    {"code": "01", "name": "Adrar", "bbox": (25.5, -2.5, 29.5, 1.5)},
    {"code": "02", "name": "Chlef", "bbox": (35.8, 0.8, 36.6, 1.8)},
    {"code": "03", "name": "Laghouat", "bbox": (33.2, 1.5, 34.6, 3.5)},
    {"code": "04", "name": "Oum El Bouaghi", "bbox": (35.4, 6.4, 36.2, 7.5)},
    {"code": "05", "name": "Batna", "bbox": (34.8, 5.2, 35.9, 6.8)},
    {"code": "06", "name": "Béjaïa", "bbox": (36.3, 4.4, 36.9, 5.5)},
    {"code": "07", "name": "Biskra", "bbox": (34.1, 4.5, 35.3, 6.3)},
    {"code": "08", "name": "Béchar", "bbox": (30.5, -3.5, 32.5, -1.0)},
    {"code": "09", "name": "Blida", "bbox": (36.3, 2.5, 36.7, 3.3)},
    {"code": "10", "name": "Bouira", "bbox": (35.9, 3.4, 36.6, 4.4)},
    {"code": "11", "name": "Tamanrasset", "bbox": (21.5, 3.0, 24.5, 7.0)},
    {"code": "12", "name": "Tébessa", "bbox": (34.5, 7.5, 35.8, 8.5)},
    {"code": "13", "name": "Tlemcen", "bbox": (34.5, -2.1, 35.3, -1.0)},
    {"code": "14", "name": "Tiaret", "bbox": (34.8, 0.9, 35.7, 2.4)},
    {"code": "15", "name": "Tizi Ouzou", "bbox": (36.5, 3.8, 36.95, 4.6)},
    {"code": "16", "name": "Alger", "bbox": (36.65, 2.8, 36.85, 3.3)},
    {"code": "17", "name": "Djelfa", "bbox": (33.8, 2.5, 35.3, 4.3)},
    {"code": "18", "name": "Jijel", "bbox": (36.5, 5.5, 36.95, 6.4)},
    {"code": "19", "name": "Sétif", "bbox": (35.7, 4.8, 36.5, 5.9)},
    {"code": "20", "name": "Saïda", "bbox": (34.5, -0.3, 35.3, 0.8)},
    {"code": "21", "name": "Skikda", "bbox": (36.5, 6.3, 37.1, 7.3)},
    {"code": "22", "name": "Sidi Bel Abbès", "bbox": (34.6, -1.1, 35.5, -0.1)},
    {"code": "23", "name": "Annaba", "bbox": (36.75, 7.4, 37.0, 7.85)},
    {"code": "24", "name": "Guelma", "bbox": (36.2, 7.1, 36.7, 7.8)},
    {"code": "25", "name": "Constantine", "bbox": (36.1, 6.4, 36.5, 6.9)},
    {"code": "26", "name": "Médéa", "bbox": (35.8, 2.5, 36.4, 3.5)},
    {"code": "27", "name": "Mostaganem", "bbox": (35.7, -0.1, 36.3, 0.6)},
    {"code": "28", "name": "M'Sila", "bbox": (34.8, 3.8, 36.1, 5.3)},
    {"code": "29", "name": "Mascara", "bbox": (35.1, -0.3, 35.7, 0.5)},
    {"code": "30", "name": "Ouargla", "bbox": (31.5, 4.8, 32.5, 5.7)},
    {"code": "31", "name": "Oran", "bbox": (35.5, -0.9, 35.9, -0.3)},
    {"code": "32", "name": "El Bayadh", "bbox": (31.5, 0.0, 33.5, 2.0)},
    {"code": "33", "name": "Illizi", "bbox": (26.0, 7.5, 28.5, 9.5)},
    {"code": "34", "name": "Bordj Bou Arréridj", "bbox": (35.8, 4.4, 36.3, 5.2)},
    {"code": "35", "name": "Boumerdès", "bbox": (36.6, 3.3, 36.95, 4.0)},
    {"code": "36", "name": "El Tarf", "bbox": (36.5, 7.8, 36.95, 8.6)},
    {"code": "37", "name": "Tindouf", "bbox": (27.2, -8.5, 28.2, -7.5)},
    {"code": "38", "name": "Tissemsilt", "bbox": (35.4, 1.4, 36.0, 2.2)},
    {"code": "39", "name": "El Oued", "bbox": (33.0, 6.5, 34.2, 7.4)},
    {"code": "40", "name": "Khenchela", "bbox": (34.8, 6.6, 35.5, 7.4)},
    {"code": "41", "name": "Souk Ahras", "bbox": (36.0, 7.7, 36.5, 8.4)},
    {"code": "42", "name": "Tipaza", "bbox": (36.4, 2.1, 36.7, 2.8)},
    {"code": "43", "name": "Mila", "bbox": (36.2, 5.9, 36.7, 6.6)},
    {"code": "44", "name": "Aïn Defla", "bbox": (36.0, 1.6, 36.5, 2.4)},
    {"code": "45", "name": "Naâma", "bbox": (32.3, -1.6, 33.7, -0.2)},
    {"code": "46", "name": "Aïn Témouchent", "bbox": (35.1, -1.4, 35.5, -0.8)},
    {"code": "47", "name": "Ghardaïa", "bbox": (32.2, 3.3, 33.0, 4.0)},
    {"code": "48", "name": "Relizane", "bbox": (35.5, 0.4, 36.1, 1.2)},
    {"code": "49", "name": "Timimoun", "bbox": (28.8, 0.8, 29.8, 1.8)},
    {"code": "50", "name": "Bordj Badji Mokhtar", "bbox": (21.0, 0.5, 22.0, 1.5)},
    {"code": "51", "name": "Ouled Djellal", "bbox": (34.2, 4.8, 34.8, 5.5)},
    {"code": "52", "name": "Béni Abbès", "bbox": (29.8, -2.5, 30.5, -1.8)},
    {"code": "53", "name": "In Salah", "bbox": (27.0, 2.2, 27.5, 2.8)},
    {"code": "54", "name": "In Guezzam", "bbox": (19.4, 5.5, 19.8, 6.0)},
    {"code": "55", "name": "Touggourt", "bbox": (32.9, 5.8, 33.3, 6.2)},
    {"code": "56", "name": "Djanet", "bbox": (24.3, 9.3, 24.8, 9.8)},
    {"code": "57", "name": "El Meghaier", "bbox": (33.8, 5.8, 34.2, 6.3)},
    {"code": "58", "name": "El Meniaa", "bbox": (30.4, 2.7, 30.8, 3.2)},
]


@dataclass
class IngestionReport:
    total_fetched: int = 0
    total_new_inserted: int = 0
    total_duplicates_skipped: int = 0
    total_errors: int = 0
    wilaya_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)


class FacilityDataStore:
    """Interface d'accès aux données supportant PostgreSQL (PostGIS) et SQLite (Fallback local)."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL")
        self.is_postgres = bool(self.db_url and self.db_url.startswith(("postgres://", "postgresql://")))
        self.pg_conn = None
        self.sqlite_conn = None

        if self.is_postgres:
            try:
                import psycopg2
                import psycopg2.extras
                self.pg_conn = psycopg2.connect(self.db_url)
                self.pg_conn.autocommit = False
                logger.info("Connexion réussie à PostgreSQL / PostGIS.")
            except Exception as e:
                logger.warning(f"Impossible de connecter PostgreSQL ({e}). Utilisation du mode SQLite / mémoire.")
                self.is_postgres = False

        if not self.is_postgres:
            import sqlite3
            if os.environ.get("SQLITE_DB_PATH"):
                sqlite_path = os.environ["SQLITE_DB_PATH"]
            elif os.path.exists("E:\\"):
                os.makedirs("E:\\medizy_data", exist_ok=True)
                sqlite_path = "E:\\medizy_data\\medizy_facilities_local.db"
            else:
                sqlite_path = "medizy_facilities_local.db"
            self.sqlite_conn = sqlite3.connect(sqlite_path)
            self._init_sqlite_tables()
            logger.info(f"Mode de stockage initialisé sur SQLite: {sqlite_path}")

    def _init_sqlite_tables(self):
        cur = self.sqlite_conn.cursor()
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_fac_coords ON facilities(latitude, longitude)")
        self.sqlite_conn.commit()

    def get_existing_facilities_for_wilaya(self, wilaya_name: str) -> List[Dict[str, Any]]:
        """Charge les établissements existants d'une wilaya pour le matching de déduplication."""
        facilities = []
        if self.is_postgres:
            import psycopg2.extras
            with self.pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT id, name, type, wilaya, commune, phone,
                           ST_Y(geom) as latitude, ST_X(geom) as longitude,
                           google_place_id, osm_id
                    FROM facilities
                    WHERE wilaya = %s
                """, (wilaya_name,))
                for row in cur.fetchall():
                    facilities.append(dict(row))
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute("""
                SELECT id, name, type, wilaya, commune, phone, latitude, longitude, google_place_id, osm_id
                FROM facilities
                WHERE wilaya = ?
            """, (wilaya_name,))
            cols = [col[0] for col in cur.description]
            for row in cur.fetchall():
                facilities.append(dict(zip(cols, row)))

        return facilities

    def insert_facility(self, facility: Dict[str, Any], wilaya_code: str = "") -> bool:
        """Insère une nouvelle structure avec `is_claimed = false`."""
        metadata_json = json.dumps(facility.get("metadata", {}), ensure_ascii=False)
        lat = facility["latitude"]
        lon = facility["longitude"]

        if self.is_postgres:
            try:
                with self.pg_conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO facilities (
                            name, type, wilaya, wilaya_code, commune, address,
                            phone, phone_normalized, geom,
                            is_claimed, is_verified, source,
                            google_place_id, osm_id, metadata
                        ) VALUES (
                            %(name)s, %(type)s, %(wilaya)s, %(wilaya_code)s, %(commune)s, %(address)s,
                            %(phone)s, %(phone_normalized)s,
                            ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326),
                            FALSE, FALSE, %(source)s,
                            %(google_place_id)s, %(osm_id)s, %(metadata)s
                        )
                        ON CONFLICT (osm_id) DO NOTHING
                    """, {
                        **facility,
                        "wilaya_code": wilaya_code,
                        "metadata": metadata_json,
                    })
                self.pg_conn.commit()
                return True
            except Exception as e:
                self.pg_conn.rollback()
                logger.error(f"Erreur insertion PostgreSQL pour '{facility.get('name')}': {e}")
                return False
        else:
            try:
                cur = self.sqlite_conn.cursor()
                cur.execute("""
                    INSERT OR IGNORE INTO facilities (
                        name, type, wilaya, wilaya_code, commune, address,
                        phone, phone_normalized, latitude, longitude,
                        is_claimed, is_verified, source,
                        google_place_id, osm_id, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?)
                """, (
                    facility["name"], facility["type"], facility["wilaya"], wilaya_code,
                    facility["commune"], facility["address"], facility["phone"],
                    facility["phone_normalized"], lat, lon, facility["source"],
                    facility.get("google_place_id"), facility.get("osm_id"), metadata_json
                ))
                self.sqlite_conn.commit()
                return cur.rowcount > 0
            except Exception as e:
                logger.error(f"Erreur insertion SQLite pour '{facility.get('name')}': {e}")
                return False

    def get_typology_breakdown_by_wilaya(self) -> Dict[str, Dict[str, int]]:
        """Retourne le décompte par type (CHU, EPH, EPSP, Polyclinique, Clinique...) par wilaya."""
        breakdown: Dict[str, Dict[str, int]] = {}
        if self.is_postgres:
            with self.pg_conn.cursor() as cur:
                cur.execute("""
                    SELECT wilaya, type, COUNT(*)
                    FROM facilities
                    GROUP BY wilaya, type
                    ORDER BY wilaya;
                """)
                for w, t, c in cur.fetchall():
                    breakdown.setdefault(w, {})[t] = c
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute("""
                SELECT wilaya, type, COUNT(*)
                FROM facilities
                GROUP BY wilaya, type
                ORDER BY wilaya;
            """)
            for w, t, c in cur.fetchall():
                breakdown.setdefault(w, {})[t] = c
        return breakdown


class HealthEnrichmentPipeline:
    """Pipeline d'enrichissement automatique national."""

    def __init__(self, datastore: FacilityDataStore, google_api_key: Optional[str] = None):
        self.datastore = datastore
        self.osm_client = OverpassClient()
        self.google_client = GooglePlacesClient(api_key=google_api_key) if google_api_key else None

    def run_for_wilaya(self, wilaya: Dict[str, Any], use_google: bool = False) -> Dict[str, int]:
        """Exécute l'ingestion et le matching pour une wilaya donnée."""
        w_name = wilaya["name"]
        w_code = wilaya["code"]
        bbox = wilaya.get("bbox")

        stats = {"fetched": 0, "inserted": 0, "duplicates": 0, "errors": 0}
        logger.info(f"--- Démarrage de l'enrichissement pour la wilaya {w_code} ({w_name}) ---")

        # 1. Collecte depuis OSM Overpass
        candidates = self.osm_client.fetch_wilaya_facilities(wilaya_name=w_name, bbox=bbox)

        # 2. Collecte complémentaire depuis Google Places si activé
        if use_google and self.google_client:
            queries = [f"hôpital {w_name}", f"clinique {w_name}", f"polyclinique {w_name}", f"CHU {w_name}"]
            for q in queries:
                try:
                    gp_res = self.google_client.text_search(query=q, wilaya=w_name)
                    candidates.extend(gp_res)
                except Exception as e:
                    logger.warning(f"Erreur Google Places sur '{q}': {e}")

        stats["fetched"] = len(candidates)

        # 3. Récupération des établissements existants pour déduplication
        existing_facilities = self.datastore.get_existing_facilities_for_wilaya(w_name)
        logger.info(f"Wilaya {w_name}: {len(existing_facilities)} structures déjà enregistrées en base.")

        # 4. Traitement et Déduplication (< 100m + similarité)
        for cand in candidates:
            cand_name = cand["name"]
            cand_lat = cand["latitude"]
            cand_lon = cand["longitude"]
            cand_gid = cand.get("google_place_id")
            cand_oid = cand.get("osm_id")

            is_duplicate = False
            for ex in existing_facilities:
                matched, dist, sim, reason = is_duplicate_match(
                    cand_lat=cand_lat,
                    cand_lon=cand_lon,
                    cand_name=cand_name,
                    cand_google_id=cand_gid,
                    cand_osm_id=cand_oid,
                    existing_facility=ex,
                    max_distance_meters=100.0,
                    min_similarity=0.68,
                )
                if matched:
                    is_duplicate = True
                    logger.debug(f"Doublon écarté: '{cand_name}' ~ '{ex.get('name')}' ({reason})")
                    break

            if is_duplicate:
                stats["duplicates"] += 1
            else:
                success = self.datastore.insert_facility(cand, wilaya_code=w_code)
                if success:
                    stats["inserted"] += 1
                    # Ajout local pour éviter doublons au sein du même batch
                    existing_facilities.append(cand)
                else:
                    stats["errors"] += 1

        logger.info(
            f"Bilan Wilaya {w_name} ({w_code}) : "
            f"Collectés: {stats['fetched']} | Nouveaux insérés: {stats['inserted']} | "
            f"Doublons filtrés: {stats['duplicates']} | Erreurs: {stats['errors']}"
        )
        return stats

    def run_national_pipeline(
        self, wilaya_filter: Optional[List[str]] = None, use_google: bool = False
    ) -> IngestionReport:
        """Lance l'ingestion complète sur l'ensemble ou une sélection des 58 wilayas."""
        report = IngestionReport()
        start_time = time.time()

        target_wilayas = ALGERIAN_WILAYAS
        if wilaya_filter:
            target_wilayas = [
                w for w in ALGERIAN_WILAYAS
                if w["code"] in wilaya_filter or w["name"].lower() in [f.lower() for f in wilaya_filter]
            ]

        logger.info(f"Démarrage du pipeline national sur {len(target_wilayas)} wilayas.")

        for wilaya in target_wilayas:
            try:
                stats = self.run_for_wilaya(wilaya, use_google=use_google)
                report.wilaya_stats[wilaya["name"]] = stats
                report.total_fetched += stats["fetched"]
                report.total_new_inserted += stats["inserted"]
                report.total_duplicates_skipped += stats["duplicates"]
                report.total_errors += stats["errors"]
                # Pause respectueuse de l'infrastructure Overpass
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Erreur critique sur la wilaya {wilaya['name']}: {e}")
                report.total_errors += 1

        elapsed = time.time() - start_time
        logger.info("==================================================================")
        logger.info(f"RAPPORT GLOBAL DU PIPELINE D'ENRICHISSEMENT (Durée: {elapsed:.1f}s)")
        logger.info(f"  - Total établissements collectés : {report.total_fetched}")
        logger.info(f"  - Total nouveaux insérés (unclaimed): {report.total_new_inserted}")
        logger.info(f"  - Total doublons éliminés (< 100m) : {report.total_duplicates_skipped}")
        logger.info(f"  - Total erreurs                   : {report.total_errors}")
        logger.info("==================================================================")
        return report


def main():
    parser = argparse.ArgumentParser(description="Pipeline national d'enrichissement de santé MEDIZY")
    parser.add_argument("--wilayas", nargs="*", help="Codes ou noms des wilayas à traiter (ex: 16 31 Alger Oran)")
    parser.add_argument("--google", action="store_true", help="Activer Google Places en complément d'OSM")
    parser.add_argument("--db-url", type=str, help="URL de connexion PostgreSQL (PostGIS)")
    args = parser.parse_args()

    datastore = FacilityDataStore(db_url=args.db_url)
    pipeline = HealthEnrichmentPipeline(datastore=datastore)
    pipeline.run_national_pipeline(wilaya_filter=args.wilayas, use_google=args.google)


if __name__ == "__main__":
    main()
