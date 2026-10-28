#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Couche d'Accès aux Données & Requêtes PostGIS
=================================================================
Moteur d'exécution des requêtes géospatiales optimisées (ST_DWithin,
ST_Distance, ST_MakeEnvelope) avec fallback SQLite pour les tests locaux.
"""

import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .schemas import FacilityBadge, FacilityResponse, FacilitySearchQuery, FacilityType

logger = logging.getLogger("medizy.api.db")


def build_badge(is_claimed: bool, is_verified: bool, facility_id: int) -> FacilityBadge:
    """Construit le badge d'affichage selon le statut de revendication."""
    if is_claimed:
        return FacilityBadge(
            label="Établissement revendiqué et vérifié",
            variant="success",
            is_claimed=True,
            is_verified=is_verified,
            can_claim=False,
            claim_url=None,
        )
    return FacilityBadge(
        label="Fiche informative publique",
        variant="info",
        is_claimed=False,
        is_verified=is_verified,
        can_claim=True,
        claim_url=f"/facilities/{facility_id}/claim",
    )


class DatabaseService:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL")
        self.is_postgres = bool(self.db_url and self.db_url.startswith(("postgres://", "postgresql://")))
        self.pg_pool = None
        if os.environ.get("SQLITE_DB_PATH"):
            self.sqlite_path = os.environ["SQLITE_DB_PATH"]
        elif os.path.exists("E:\\"):
            os.makedirs("E:\\medizy_data", exist_ok=True)
            self.sqlite_path = "E:\\medizy_data\\medizy_facilities_local.db"
        else:
            self.sqlite_path = "medizy_facilities_local.db"

        if self.is_postgres:
            try:
                import psycopg2
                from psycopg2 import pool
                # Pool de connexions réutilisables (min 2, max 20)
                self.pg_pool = pool.ThreadedConnectionPool(2, 20, self.db_url)
                logger.info("Pool PostgreSQL initialisé avec succès.")
            except Exception as e:
                logger.warning(f"Échec initialisation PostgreSQL ({e}). Bascule vers SQLite ({self.sqlite_path}).")
                self.is_postgres = False

    def _get_pg_connection(self):
        return self.pg_pool.getconn()

    def _release_pg_connection(self, conn):
        self.pg_pool.putconn(conn)

    def _get_sqlite_connection(self):
        import sqlite3
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def search_facilities(self, query: FacilitySearchQuery) -> Tuple[int, List[FacilityResponse]]:
        """
        Recherche géospatiale avancée supportant :
          - Requêtes par rayon métrique (ST_DWithin)
          - Requêtes par Bounding Box pour viewport de carte (ST_MakeEnvelope)
          - Filtrage par type, wilaya, commune, texte libre (q) et is_claimed
        """
        if self.is_postgres:
            return self._search_postgres(query)
        return self._search_sqlite(query)

    def _search_postgres(self, q: FacilitySearchQuery) -> Tuple[int, List[FacilityResponse]]:
        import psycopg2.extras
        conn = self._get_pg_connection()
        try:
            where_clauses = ["1=1"]
            params: Dict[str, Any] = {
                "limit": q.limit,
                "offset": q.offset,
            }

            select_distance = "NULL::double precision AS distance_meters"
            order_by = "f.is_claimed DESC, f.name ASC"

            # 1. Requête par proximité GPS (Rayon R)
            if q.lat is not None and q.lon is not None:
                params["lat"] = q.lat
                params["lon"] = q.lon
                params["radius_meters"] = q.radius_km * 1000.0

                where_clauses.append(
                    "ST_DWithin(f.geom::geography, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, %(radius_meters)s)"
                )
                select_distance = (
                    "ST_Distance(f.geom::geography, ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography) AS distance_meters"
                )
                order_by = "distance_meters ASC"

            # 2. Requête par Bounding Box (Viewport carte)
            elif None not in (q.min_lat, q.min_lon, q.max_lat, q.max_lon):
                params.update({
                    "min_lat": q.min_lat,
                    "min_lon": q.min_lon,
                    "max_lat": q.max_lat,
                    "max_lon": q.max_lon,
                })
                where_clauses.append(
                    "f.geom && ST_MakeEnvelope(%(min_lon)s, %(min_lat)s, %(max_lon)s, %(max_lat)s, 4326)"
                )

            # 3. Filtre par type d'établissement
            if q.type:
                where_clauses.append("f.type = %(type)s")
                params["type"] = q.type.value

            # 4. Filtre par Wilaya
            if q.wilaya:
                where_clauses.append("(f.wilaya ILIKE %(wilaya)s OR f.wilaya_code = %(wilaya_clean)s)")
                params["wilaya"] = f"%{q.wilaya}%"
                params["wilaya_clean"] = q.wilaya.strip()

            # 5. Filtre par Commune
            if q.commune:
                where_clauses.append("f.commune ILIKE %(commune)s")
                params["commune"] = f"%{q.commune}%"

            # 6. Filtre de statut de revendication (is_claimed)
            # IMPORTANT: Par défaut (None), on n'exclut JAMAIS les fiches non revendiquées !
            if q.is_claimed is not None:
                where_clauses.append("f.is_claimed = %(is_claimed)s")
                params["is_claimed"] = q.is_claimed

            # 7. Recherche textuelle plein texte / trigramme
            if q.q:
                where_clauses.append("(f.name ILIKE %(q)s OR f.address ILIKE %(q)s OR f.commune ILIKE %(q)s)")
                params["q"] = f"%{q.q}%"

            where_sql = " AND ".join(where_clauses)

            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Décompte total
                count_query = f"SELECT COUNT(*) FROM facilities f WHERE {where_sql}"
                cur.execute(count_query, params)
                total_count = cur.fetchone()[0]

                # Données paginées
                data_query = f"""
                    SELECT 
                        f.id, f.name, f.type, f.wilaya, f.wilaya_code, f.commune, f.address, f.phone,
                        ST_Y(f.geom) AS latitude, ST_X(f.geom) AS longitude,
                        f.is_claimed, f.is_verified, f.source, f.google_place_id, f.osm_id,
                        f.metadata, f.created_at,
                        {select_distance}
                    FROM facilities f
                    WHERE {where_sql}
                    ORDER BY {order_by}
                    LIMIT %(limit)s OFFSET %(offset)s
                """
                cur.execute(data_query, params)
                rows = cur.fetchall()

            results = []
            for r in rows:
                row_dict = dict(r)
                badge = build_badge(row_dict["is_claimed"], row_dict["is_verified"], row_dict["id"])
                results.append(FacilityResponse(**row_dict, badge=badge))

            return total_count, results
        finally:
            self._release_pg_connection(conn)

    def _search_sqlite(self, q: FacilitySearchQuery) -> Tuple[int, List[FacilityResponse]]:
        """Moteur spatial de secours en SQLite avec calcul Haversine direct."""
        conn = self._get_sqlite_connection()
        try:
            where_clauses = ["1=1"]
            params: List[Any] = []

            # Filtrage Bounding Box ou pré-filtrage spatial
            if q.lat is not None and q.lon is not None:
                # Delta approximatif en degrés pour pré-filtrage index B-Tree (1 degré lat ~ 111km)
                deg_delta = (q.radius_km / 111.0) * 1.2
                where_clauses.append("latitude BETWEEN ? AND ?")
                params.extend([q.lat - deg_delta, q.lat + deg_delta])
                where_clauses.append("longitude BETWEEN ? AND ?")
                params.extend([q.lon - deg_delta, q.lon + deg_delta])
            elif None not in (q.min_lat, q.min_lon, q.max_lat, q.max_lon):
                where_clauses.append("latitude BETWEEN ? AND ?")
                params.extend([q.min_lat, q.max_lat])
                where_clauses.append("longitude BETWEEN ? AND ?")
                params.extend([q.min_lon, q.max_lon])

            if q.type:
                where_clauses.append("type = ?")
                params.append(q.type.value)

            if q.wilaya:
                where_clauses.append("(wilaya LIKE ? OR wilaya_code = ?)")
                params.extend([f"%{q.wilaya}%", q.wilaya.strip()])

            if q.commune:
                where_clauses.append("commune LIKE ?")
                params.append(f"%{q.commune}%")

            if q.is_claimed is not None:
                where_clauses.append("is_claimed = ?")
                params.append(1 if q.is_claimed else 0)

            if q.q:
                where_clauses.append("(name LIKE ? OR address LIKE ? OR commune LIKE ?)")
                params.extend([f"%{q.q}%", f"%{q.q}%", f"%{q.q}%"])

            where_sql = " AND ".join(where_clauses)
            cur = conn.cursor()

            cur.execute(f"SELECT * FROM facilities WHERE {where_sql}", params)
            all_rows = cur.fetchall()

            # Calcul de distance et filtrage précis
            processed = []
            for row in all_rows:
                r_dict = dict(row)
                dist_m = None
                if q.lat is not None and q.lon is not None:
                    lat2 = r_dict["latitude"]
                    lon2 = r_dict["longitude"]
                    # Haversine
                    phi1, phi2 = math.radians(q.lat), math.radians(lat2)
                    dphi = math.radians(lat2 - q.lat)
                    dlam = math.radians(lon2 - q.lon)
                    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2)**2
                    dist_m = 6371000.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    if dist_m > (q.radius_km * 1000.0):
                        continue

                r_dict["distance_meters"] = dist_m
                r_dict["is_claimed"] = bool(r_dict.get("is_claimed"))
                r_dict["is_verified"] = bool(r_dict.get("is_verified"))
                if isinstance(r_dict.get("metadata"), str):
                    try:
                        r_dict["metadata"] = json.loads(r_dict["metadata"])
                    except:
                        r_dict["metadata"] = {}

                badge = build_badge(r_dict["is_claimed"], r_dict["is_verified"], r_dict["id"])
                processed.append(FacilityResponse(**r_dict, badge=badge))

            if q.lat is not None and q.lon is not None:
                processed.sort(key=lambda x: x.distance_meters if x.distance_meters is not None else float("inf"))
            else:
                processed.sort(key=lambda x: (not x.is_claimed, x.name))

            total = len(processed)
            paged = processed[q.offset : q.offset + q.limit]
            return total, paged
        finally:
            conn.close()

    def get_facility_by_id(self, facility_id: int) -> Optional[FacilityResponse]:
        """Récupère une structure de santé par son identifiant unique."""
        if self.is_postgres:
            import psycopg2.extras
            conn = self._get_pg_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT f.id, f.name, f.type, f.wilaya, f.wilaya_code, f.commune, f.address, f.phone,
                               ST_Y(f.geom) AS latitude, ST_X(f.geom) AS longitude,
                               f.is_claimed, f.is_verified, f.source, f.google_place_id, f.osm_id,
                               f.metadata, f.created_at, NULL::double precision as distance_meters
                        FROM facilities f
                        WHERE f.id = %s
                    """, (facility_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    r_dict = dict(row)
                    badge = build_badge(r_dict["is_claimed"], r_dict["is_verified"], r_dict["id"])
                    return FacilityResponse(**r_dict, badge=badge)
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM facilities WHERE id = ?", (facility_id,))
                row = cur.fetchone()
                if not row:
                    return None
                r_dict = dict(row)
                r_dict["distance_meters"] = None
                r_dict["is_claimed"] = bool(r_dict.get("is_claimed"))
                r_dict["is_verified"] = bool(r_dict.get("is_verified"))
                if isinstance(r_dict.get("metadata"), str):
                    try:
                        r_dict["metadata"] = json.loads(r_dict["metadata"])
                    except:
                        r_dict["metadata"] = {}
                badge = build_badge(r_dict["is_claimed"], r_dict["is_verified"], r_dict["id"])
                return FacilityResponse(**r_dict, badge=badge)
            finally:
                conn.close()

    def insert_suggestion(
        self,
        name: str,
        facility_type: Optional[str],
        wilaya: str,
        commune: Optional[str],
        address: Optional[str],
        phone: Optional[str],
        lat: Optional[float],
        lon: Optional[float],
        google_maps_url: Optional[str],
        submitter_name: Optional[str],
        submitter_email: Optional[str],
        submitter_phone: Optional[str],
        submitter_notes: Optional[str],
        matched_facility_id: Optional[int] = None,
    ) -> int:
        """Enregistre une suggestion citoyenne dans la table de modération `facility_suggestions`."""
        if self.is_postgres:
            conn = self._get_pg_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO facility_suggestions (
                            name, type, wilaya, commune, address, phone,
                            latitude, longitude,
                            geom, google_maps_url,
                            submitter_name, submitter_email, submitter_phone, submitter_notes,
                            status, matched_facility_id
                        ) VALUES (
                            %(name)s, %(type)s, %(wilaya)s, %(commune)s, %(address)s, %(phone)s,
                            %(lat)s, %(lon)s,
                            CASE WHEN %(lat)s IS NOT NULL AND %(lon)s IS NOT NULL 
                                 THEN ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326) 
                                 ELSE NULL END,
                            %(google_maps_url)s,
                            %(submitter_name)s, %(submitter_email)s, %(submitter_phone)s, %(submitter_notes)s,
                            'PENDING', %(matched_facility_id)s
                        )
                        RETURNING id
                    """, {
                        "name": name, "type": facility_type, "wilaya": wilaya, "commune": commune,
                        "address": address, "phone": phone, "lat": lat, "lon": lon,
                        "google_maps_url": google_maps_url, "submitter_name": submitter_name,
                        "submitter_email": submitter_email, "submitter_phone": submitter_phone,
                        "submitter_notes": submitter_notes, "matched_facility_id": matched_facility_id,
                    })
                    new_id = cur.fetchone()[0]
                conn.commit()
                return new_id
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                self._ensure_sqlite_suggestions_schema(conn)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO facility_suggestions (
                        name, type, wilaya, commune, address, phone,
                        latitude, longitude, google_maps_url,
                        submitter_name, submitter_email, submitter_phone, submitter_notes,
                        status, matched_facility_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                """, (
                    name, facility_type, wilaya, commune, address, phone,
                    lat, lon, google_maps_url, submitter_name, submitter_email,
                    submitter_phone, submitter_notes, matched_facility_id
                ))
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def _ensure_sqlite_suggestions_schema(self, conn):
        """Initialise la table facility_suggestions et ajoute dynamiquement les colonnes de modération si absentes."""
        cur = conn.cursor()
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
                moderated_by TEXT,
                moderated_at TEXT,
                moderation_comment TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cur.execute("PRAGMA table_info(facility_suggestions)")
        cols = [c[1] for c in cur.fetchall()]
        for col in ["moderated_by", "moderated_at", "moderation_comment", "updated_at"]:
            if col not in cols:
                cur.execute(f"ALTER TABLE facility_suggestions ADD COLUMN {col} TEXT")
        conn.commit()

    def get_facility_by_id(self, facility_id: int) -> Optional[FacilityResponse]:
        """Récupère une structure par son identifiant unique avec calcul du badge."""
        if self.is_postgres:
            conn = self._get_pg_connection()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT id, name, type, wilaya, wilaya_code, commune, address, phone,
                               ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
                               is_claimed, is_verified, source, google_place_id, osm_id,
                               metadata, created_at
                        FROM facilities WHERE id = %s
                    """, (facility_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return FacilityResponse(
                        id=row["id"],
                        name=row["name"],
                        type=row["type"],
                        wilaya=row["wilaya"],
                        wilaya_code=row["wilaya_code"],
                        commune=row["commune"],
                        address=row["address"],
                        phone=row["phone"],
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        is_claimed=row["is_claimed"],
                        is_verified=row["is_verified"],
                        source=row["source"],
                        google_place_id=row["google_place_id"],
                        osm_id=row["osm_id"],
                        badge=build_badge(row["is_claimed"], row["is_verified"], row["id"]),
                        metadata=row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"] or "{}"),
                        created_at=row["created_at"],
                    )
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, name, type, wilaya, wilaya_code, commune, address, phone,
                           latitude, longitude, is_claimed, is_verified, source,
                           google_place_id, osm_id, metadata, created_at
                    FROM facilities WHERE id = ?
                """, (facility_id,))
                row = cur.fetchone()
                if not row:
                    return None
                meta = row["metadata"]
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                return FacilityResponse(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    wilaya=row["wilaya"],
                    wilaya_code=row["wilaya_code"],
                    commune=row["commune"],
                    address=row["address"],
                    phone=row["phone"],
                    latitude=row["latitude"],
                    longitude=row["longitude"],
                    is_claimed=bool(row["is_claimed"]),
                    is_verified=bool(row["is_verified"]),
                    source=row["source"],
                    google_place_id=row["google_place_id"],
                    osm_id=row["osm_id"],
                    badge=build_badge(bool(row["is_claimed"]), bool(row["is_verified"]), row["id"]),
                    metadata=meta,
                    created_at=row["created_at"],
                )
            finally:
                conn.close()

    def list_suggestions(
        self, status_filter: Optional[str] = "PENDING", limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Liste les suggestions citoyennes avec enrichissement des doublons repérés."""
        items: List[Dict[str, Any]] = []
        total = 0

        if self.is_postgres:
            conn = self._get_pg_connection()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    where = "1=1"
                    params = []
                    if status_filter and status_filter.upper() != "ALL":
                        where = "status = %s"
                        params.append(status_filter.upper())

                    cur.execute(f"SELECT COUNT(*) FROM facility_suggestions WHERE {where}", params)
                    total = cur.fetchone()[0]

                    query = f"""
                        SELECT id, name, type, wilaya, commune, address, phone,
                               latitude, longitude, google_maps_url,
                               submitter_name, submitter_email, submitter_phone, submitter_notes,
                               status, matched_facility_id, moderated_by, moderated_at, moderation_comment,
                               created_at
                        FROM facility_suggestions
                        WHERE {where}
                        ORDER BY id DESC
                        LIMIT %s OFFSET %s
                    """
                    cur.execute(query, params + [limit, offset])
                    for r in cur.fetchall():
                        d = dict(r)
                        if d.get("matched_facility_id"):
                            d["potential_duplicate"] = self.get_facility_by_id(d["matched_facility_id"])
                        items.append(d)
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                self._ensure_sqlite_suggestions_schema(conn)
                cur = conn.cursor()

                where_sql = "1=1"
                params = []
                if status_filter and status_filter.upper() != "ALL":
                    where_sql = "status = ?"
                    params.append(status_filter.upper())

                cur.execute(f"SELECT COUNT(*) FROM facility_suggestions WHERE {where_sql}", params)
                total = cur.fetchone()[0]

                sql = f"""
                    SELECT id, name, type, wilaya, commune, address, phone,
                           latitude, longitude, google_maps_url,
                           submitter_name, submitter_email, submitter_phone, submitter_notes,
                           status, matched_facility_id, moderated_by, moderated_at, moderation_comment,
                           created_at
                    FROM facility_suggestions
                    WHERE {where_sql}
                    ORDER BY id DESC
                    LIMIT ? OFFSET ?
                """
                cur.execute(sql, params + [limit, offset])
                for r in cur.fetchall():
                    d = dict(r)
                    if d.get("matched_facility_id"):
                        d["potential_duplicate"] = self.get_facility_by_id(d["matched_facility_id"])
                    items.append(d)
            finally:
                conn.close()

        return total, items

    def get_suggestion_by_id(self, suggestion_id: int) -> Optional[Dict[str, Any]]:
        """Récupère une suggestion citoyenne par son identifiant."""
        if self.is_postgres:
            conn = self._get_pg_connection()
            try:
                import psycopg2.extras
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("SELECT * FROM facility_suggestions WHERE id = %s", (suggestion_id,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    d = dict(row)
                    if d.get("matched_facility_id"):
                        d["potential_duplicate"] = self.get_facility_by_id(d["matched_facility_id"])
                    return d
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                self._ensure_sqlite_suggestions_schema(conn)
                cur = conn.cursor()
                cur.execute("SELECT * FROM facility_suggestions WHERE id = ?", (suggestion_id,))
                row = cur.fetchone()
                if not row:
                    return None
                d = dict(row)
                if d.get("matched_facility_id"):
                    d["potential_duplicate"] = self.get_facility_by_id(d["matched_facility_id"])
                return d
            finally:
                conn.close()

    def approve_suggestion(
        self,
        suggestion_id: int,
        moderator_name: str = "Admin MEDIZY",
        comment: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Tuple[FacilityResponse, Dict[str, Any]]:
        """
        Approuve une suggestion citoyenne :
        1. Crée un nouvel établissement officiel dans `facilities` (source='community_suggestion', is_verified=true).
        2. Met à jour le statut de la suggestion en 'APPROVED' avec traçabilité.
        """
        sugg = self.get_suggestion_by_id(suggestion_id)
        if not sugg:
            raise ValueError(f"Suggestion {suggestion_id} introuvable.")

        overrides = overrides or {}
        name = overrides.get("name") or sugg["name"]
        fac_type = overrides.get("type") or sugg["type"] or "Polyclinique"
        address = overrides.get("address") or sugg["address"] or ""
        phone = overrides.get("phone") or sugg["phone"] or ""
        wilaya = sugg["wilaya"]
        commune = sugg.get("commune") or ""
        lat = sugg.get("latitude") or 36.75
        lon = sugg.get("longitude") or 3.05

        meta = {
            "approved_by": moderator_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "original_suggestion_id": suggestion_id,
            "submitter_name": sugg.get("submitter_name"),
            "submitter_notes": sugg.get("submitter_notes"),
            "moderation_comment": comment,
        }
        metadata_str = json.dumps(meta, ensure_ascii=False)

        created_facility_id: int = 0

        if self.is_postgres:
            conn = self._get_pg_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO facilities (
                            name, type, wilaya, commune, address, phone,
                            geom, is_claimed, is_verified, source, metadata
                        ) VALUES (
                            %(name)s, %(type)s, %(wilaya)s, %(commune)s, %(address)s, %(phone)s,
                            ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326),
                            FALSE, TRUE, 'community_suggestion', %(metadata)s
                        ) RETURNING id
                    """, {
                        "name": name, "type": fac_type, "wilaya": wilaya, "commune": commune,
                        "address": address, "phone": phone, "lat": lat, "lon": lon,
                        "metadata": metadata_str,
                    })
                    created_facility_id = cur.fetchone()[0]

                    cur.execute("""
                        UPDATE facility_suggestions
                        SET status = 'APPROVED',
                            moderated_by = %s,
                            moderated_at = CURRENT_TIMESTAMP,
                            moderation_comment = %s,
                            matched_facility_id = %s
                        WHERE id = %s
                    """, (moderator_name, comment, created_facility_id, suggestion_id))
                conn.commit()
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO facilities (
                        name, type, wilaya, commune, address, phone,
                        latitude, longitude, is_claimed, is_verified, source, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 'community_suggestion', ?)
                """, (
                    name, fac_type, wilaya, commune, address, phone,
                    lat, lon, metadata_str
                ))
                created_facility_id = cur.lastrowid

                cur.execute("""
                    UPDATE facility_suggestions
                    SET status = 'APPROVED',
                        moderated_by = ?,
                        moderated_at = datetime('now'),
                        moderation_comment = ?,
                        matched_facility_id = ?
                    WHERE id = ?
                """, (moderator_name, comment, created_facility_id, suggestion_id))
                conn.commit()
            finally:
                conn.close()

        facility = self.get_facility_by_id(created_facility_id)
        updated_sugg = self.get_suggestion_by_id(suggestion_id)
        return facility, updated_sugg

    def reject_suggestion(
        self,
        suggestion_id: int,
        reason: str,
        moderator_name: str = "Admin MEDIZY",
    ) -> Dict[str, Any]:
        """Rejette une suggestion citoyenne avec motif explicite."""
        sugg = self.get_suggestion_by_id(suggestion_id)
        if not sugg:
            raise ValueError(f"Suggestion {suggestion_id} introuvable.")

        if self.is_postgres:
            conn = self._get_pg_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE facility_suggestions
                        SET status = 'REJECTED',
                            moderated_by = %s,
                            moderated_at = CURRENT_TIMESTAMP,
                            moderation_comment = %s
                        WHERE id = %s
                    """, (moderator_name, reason, suggestion_id))
                conn.commit()
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE facility_suggestions
                    SET status = 'REJECTED',
                        moderated_by = ?,
                        moderated_at = datetime('now'),
                        moderation_comment = ?
                    WHERE id = ?
                """, (moderator_name, reason, suggestion_id))
                conn.commit()
            finally:
                conn.close()

        return self.get_suggestion_by_id(suggestion_id)

    def find_potential_duplicate(self, name: str, lat: Optional[float], lon: Optional[float], wilaya: str) -> Optional[int]:
        """Vérifie si une structure équivalente existe déjà à moins de 100m pour alerter le modérateur."""
        if lat is None or lon is None:
            return None

        query = FacilitySearchQuery(
            lat=lat,
            lon=lon,
            radius_km=0.15,  # 150 mètres
            wilaya=wilaya,
            limit=5,
        )
        _, nearby = self.search_facilities(query)
        for fac in nearby:
            if fac.distance_meters is not None and fac.distance_meters <= 100.0:
                return fac.id
    def export_facilities_incremental(
        self,
        cursor: Optional[int] = None,
        updated_since: Optional[str] = None,
        wilaya: Optional[str] = None,
        limit: int = 100,
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[str]]:
        """
        Extrait un flux incrémental de structures de santé pour l'index sémantique de l'agent NIBRAS.
        Utilise une pagination par curseur strictly monotone (id > cursor) et un filtre temporel updated_since.
        """
        limit = min(max(1, limit), 500)
        fetch_limit = limit + 1

        if self.is_postgres:
            import psycopg2.extras
            conn = self._get_pg_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    where_clauses = ["1=1"]
                    params: List[Any] = []

                    if cursor is not None:
                        where_clauses.append("f.id > %s")
                        params.append(cursor)

                    if updated_since:
                        where_clauses.append("(f.updated_at >= %s OR (f.updated_at IS NULL AND f.created_at >= %s))")
                        params.extend([updated_since, updated_since])

                    if wilaya:
                        where_clauses.append("(LOWER(f.wilaya) = LOWER(%s) OR f.wilaya_code = %s)")
                        params.extend([wilaya, wilaya])

                    where_sql = " AND ".join(where_clauses)
                    query = f"""
                        SELECT f.id, f.name, f.type, f.wilaya, f.wilaya_code, f.commune, f.address, f.phone,
                               ST_Y(f.geom) AS latitude, ST_X(f.geom) AS longitude,
                               f.is_claimed, f.is_verified, f.source, f.created_at, f.updated_at
                        FROM facilities f
                        WHERE {where_sql}
                        ORDER BY f.id ASC
                        LIMIT %s
                    """
                    params.append(fetch_limit)
                    cur.execute(query, tuple(params))
                    rows = [dict(r) for r in cur.fetchall()]
            finally:
                self._release_pg_connection(conn)
        else:
            conn = self._get_sqlite_connection()
            try:
                cur = conn.cursor()
                where_clauses = ["1=1"]
                params = []

                if cursor is not None:
                    where_clauses.append("id > ?")
                    params.append(cursor)

                if updated_since:
                    where_clauses.append("(updated_at >= ? OR (updated_at IS NULL AND created_at >= ?))")
                    params.extend([updated_since, updated_since])

                if wilaya:
                    where_clauses.append("(LOWER(wilaya) = LOWER(?) OR wilaya_code = ?)")
                    params.extend([wilaya, wilaya])

                where_sql = " AND ".join(where_clauses)
                query = f"""
                    SELECT id, name, type, wilaya, wilaya_code, commune, address, phone,
                           latitude, longitude, is_claimed, is_verified, source, created_at, updated_at
                    FROM facilities
                    WHERE {where_sql}
                    ORDER BY id ASC
                    LIMIT ?
                """
                params.append(fetch_limit)
                cur.execute(query, tuple(params))
                rows = [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()

        has_more = len(rows) > limit
        result_items = rows[:limit]

        # Formatage des éléments avec contexte sémantique pour NIBRAS
        formatted_items = []
        for r in result_items:
            commune_part = f" à {r['commune']}" if r.get("commune") else ""
            addr_part = f" Adresse : {r['address']}." if r.get("address") else ""
            phone_part = f" Téléphone : {r['phone']}." if r.get("phone") else ""
            verified_part = "Établissement vérifié et certifié." if r.get("is_verified") else "Fiche d'information publique."
            embedding_ctx = (
                f"{r.get('type', 'Établissement de santé')} '{r['name']}'{commune_part}, Wilaya de {r['wilaya']}."
                f"{addr_part}{phone_part} Statut : {verified_part}"
            )

            r_clean = {
                "id": r["id"],
                "name": r["name"],
                "type": r.get("type") or "Établissement",
                "wilaya": r["wilaya"],
                "wilaya_code": r.get("wilaya_code"),
                "commune": r.get("commune"),
                "address": r.get("address"),
                "phone": r.get("phone"),
                "latitude": float(r["latitude"]) if r.get("latitude") is not None else 0.0,
                "longitude": float(r["longitude"]) if r.get("longitude") is not None else 0.0,
                "is_claimed": bool(r.get("is_claimed")),
                "is_verified": bool(r.get("is_verified")),
                "source": r.get("source") or "osm",
                "created_at": str(r["created_at"]) if r.get("created_at") else None,
                "updated_at": str(r["updated_at"]) if r.get("updated_at") else None,
                "embedding_context": embedding_ctx,
            }
            formatted_items.append(r_clean)

        next_cursor = str(result_items[-1]["id"]) if (has_more and result_items) else None
        return formatted_items, has_more, next_cursor

    def close(self):
        """Ferme proprement les connexions et pools actifs."""
        if self.pg_pool:
            try:
                self.pg_pool.closeall()
                logger.info("Pool de connexions PostgreSQL fermé avec succès.")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture du pool PostgreSQL: {e}")


_db_service_instance: Optional[DatabaseService] = None


def get_db_service() -> DatabaseService:
    """Fournisseur de singleton pour le service de base de données."""
    global _db_service_instance
    expected_sqlite = os.environ.get("SQLITE_DB_PATH")
    if _db_service_instance is not None and expected_sqlite and _db_service_instance.sqlite_path != expected_sqlite:
        _db_service_instance.close()
        _db_service_instance = None

    if _db_service_instance is None:
        _db_service_instance = DatabaseService()
    return _db_service_instance


def close_db_service():
    """Ferme l'instance singleton lors de l'arrêt de l'application."""
    global _db_service_instance
    if _db_service_instance is not None:
        _db_service_instance.close()
        _db_service_instance = None
