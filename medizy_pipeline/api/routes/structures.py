#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Endpoint API /api/structures
=================================================
Filtrage dynamique par wilaya, commune, catégorie, spécialité et proximité GPS
sur la table `structures` issue de l'Annuaire Sanitaire National des 58 wilayas.

Montage dans main.py :
    from .routes.structures import router as structures_router
    app.include_router(structures_router)
"""

import math
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..db import DatabaseService, get_db_service

router = APIRouter(prefix="/api/structures", tags=["Annuaire Sanitaire National"])


# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic dédiés à la table `structures`
# ─────────────────────────────────────────────────────────────────────────────

class StructureItem(BaseModel):
    """Représentation publique d'une structure ou d'un praticien de l'annuaire."""
    id: int
    code_wilaya: str
    nom_wilaya: str
    nom_daira: Optional[str] = None
    nom_commune: Optional[str] = None
    categorie: str
    discipline_specialite: Optional[str] = None
    nom_etablissement_praticien: str
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    horaires: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    statut_remarques: Optional[str] = None
    source_csv: Optional[str] = None
    is_verified: bool = False
    distance_meters: Optional[float] = Field(
        None, description="Distance en mètres (rempli uniquement pour les requêtes GPS)"
    )


class StructureListResponse(BaseModel):
    """Réponse paginée de la liste des structures."""
    total: int
    limit: int
    offset: int
    execution_time_ms: float
    data: List[StructureItem]


class WilayaStats(BaseModel):
    code_wilaya: str
    nom_wilaya: str
    total: int
    avec_gps: int
    nb_categories: int
    nb_communes: int


class CategorieStats(BaseModel):
    categorie: str
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance Haversine entre deux points GPS en mètres (fallback SQLite)."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _row_to_item(row: Any, columns: List[str], dist_m: Optional[float] = None) -> StructureItem:
    """Convertit une ligne DB en StructureItem."""
    if isinstance(row, dict):
        d = row
    else:
        d = dict(zip(columns, row))

    return StructureItem(
        id=d["id"],
        code_wilaya=d.get("code_wilaya", ""),
        nom_wilaya=d.get("nom_wilaya", ""),
        nom_daira=d.get("nom_daira") or None,
        nom_commune=d.get("nom_commune") or None,
        categorie=d.get("categorie", ""),
        discipline_specialite=d.get("discipline_specialite") or None,
        nom_etablissement_praticien=d.get("nom_etablissement_praticien", ""),
        adresse=d.get("adresse") or None,
        telephone=d.get("telephone") or None,
        horaires=d.get("horaires") or None,
        latitude=d.get("latitude"),
        longitude=d.get("longitude"),
        statut_remarques=d.get("statut_remarques") or None,
        source_csv=d.get("source_csv") or None,
        is_verified=bool(d.get("is_verified", False)),
        distance_meters=dist_m if dist_m is not None else d.get("distance_meters"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Requêtes DB (PostgreSQL + SQLite)
# ─────────────────────────────────────────────────────────────────────────────

def _query_structures_pg(
    db: DatabaseService,
    *,
    q: Optional[str] = None,
    code_wilaya: Optional[str] = None,
    nom_wilaya: Optional[str] = None,
    nom_commune: Optional[str] = None,
    categorie: Optional[str] = None,
    discipline: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 10.0,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, List[StructureItem]]:
    """Exécute la requête de filtrage dynamique sur PostgreSQL/PostGIS."""
    conditions = []
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    if q:
        conditions.append(
            "(unaccent(nom_etablissement_praticien) ILIKE unaccent(%(q)s) "
            "OR unaccent(adresse) ILIKE unaccent(%(q)s) "
            "OR unaccent(discipline_specialite) ILIKE unaccent(%(q)s))"
        )
        params["q"] = f"%{q}%"

    if code_wilaya:
        conditions.append("code_wilaya = %(code_wilaya)s")
        params["code_wilaya"] = code_wilaya.zfill(2)

    if nom_wilaya:
        conditions.append("nom_wilaya ILIKE %(nom_wilaya)s")
        params["nom_wilaya"] = f"%{nom_wilaya}%"

    if nom_commune:
        conditions.append("nom_commune ILIKE %(nom_commune)s")
        params["nom_commune"] = f"%{nom_commune}%"

    if categorie:
        conditions.append("categorie ILIKE %(categorie)s")
        params["categorie"] = f"%{categorie}%"

    if discipline:
        conditions.append("discipline_specialite ILIKE %(discipline)s")
        params["discipline"] = f"%{discipline}%"

    geo_join = ""
    order_by = "ORDER BY nom_etablissement_praticien"
    dist_select = "NULL::DOUBLE PRECISION AS distance_meters"

    if lat is not None and lon is not None:
        conditions.append(
            "geom IS NOT NULL AND ST_DWithin("
            "geom::geography, "
            "ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography, "
            "%(radius_m)s)"
        )
        dist_select = (
            "ST_Distance(geom::geography, "
            "ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography) "
            "AS distance_meters"
        )
        order_by = "ORDER BY distance_meters"
        params["lat"] = lat
        params["lon"] = lon
        params["radius_m"] = radius_km * 1000.0

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    count_sql = f"SELECT COUNT(*) FROM structures {where}"
    data_sql = f"""
        SELECT
            id, code_wilaya, nom_wilaya, nom_daira, nom_commune,
            categorie, discipline_specialite, nom_etablissement_praticien,
            adresse, telephone, horaires,
            latitude, longitude, statut_remarques, source_csv, is_verified,
            {dist_select}
        FROM structures
        {where}
        {order_by}
        LIMIT %(limit)s OFFSET %(offset)s
    """

    conn = db._get_pg_connection()
    try:
        with conn.cursor() as cur:
            import psycopg2.extras
            cur.execute(count_sql, params)
            total = cur.fetchone()[0]

            cur.execute(data_sql, params)
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            items = [_row_to_item(dict(zip(cols, r)), cols) for r in rows]
    finally:
        db._return_pg_connection(conn)

    return total, items


def _query_structures_sqlite(
    db: DatabaseService,
    *,
    q: Optional[str] = None,
    code_wilaya: Optional[str] = None,
    nom_wilaya: Optional[str] = None,
    nom_commune: Optional[str] = None,
    categorie: Optional[str] = None,
    discipline: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 10.0,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, List[StructureItem]]:
    """Exécute la requête de filtrage sur SQLite (mode local)."""
    import sqlite3

    conditions = []
    params: List[Any] = []

    if q:
        conditions.append(
            "(LOWER(nom_etablissement_praticien) LIKE LOWER(?) "
            "OR LOWER(adresse) LIKE LOWER(?) "
            "OR LOWER(discipline_specialite) LIKE LOWER(?))"
        )
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    if code_wilaya:
        conditions.append("code_wilaya = ?")
        params.append(code_wilaya.zfill(2))

    if nom_wilaya:
        conditions.append("LOWER(nom_wilaya) LIKE LOWER(?)")
        params.append(f"%{nom_wilaya}%")

    if nom_commune:
        conditions.append("LOWER(nom_commune) LIKE LOWER(?)")
        params.append(f"%{nom_commune}%")

    if categorie:
        conditions.append("LOWER(categorie) LIKE LOWER(?)")
        params.append(f"%{categorie}%")

    if discipline:
        conditions.append("LOWER(discipline_specialite) LIKE LOWER(?)")
        params.append(f"%{discipline}%")

    # Pré-filtrage BBox pour approximer le rayon (SQLite n'a pas PostGIS)
    if lat is not None and lon is not None:
        deg_lat = radius_km / 111.32
        deg_lon = radius_km / (111.32 * math.cos(math.radians(lat)))
        conditions.extend([
            "latitude IS NOT NULL",
            "latitude BETWEEN ? AND ?",
            "longitude BETWEEN ? AND ?",
        ])
        params.extend([
            lat - deg_lat, lat + deg_lat,
            lon - deg_lon, lon + deg_lon,
        ])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    count_sql = f"SELECT COUNT(*) FROM structures {where}"
    data_sql = f"""
        SELECT
            id, code_wilaya, nom_wilaya, nom_daira, nom_commune,
            categorie, discipline_specialite, nom_etablissement_praticien,
            adresse, telephone, horaires,
            latitude, longitude, statut_remarques, source_csv, is_verified
        FROM structures
        {where}
        ORDER BY nom_etablissement_praticien
        LIMIT ? OFFSET ?
    """

    conn = sqlite3.connect(db.sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        cur.execute(data_sql, params + [limit, offset])
        rows = cur.fetchall()
    finally:
        conn.close()

    items = []
    for r in rows:
        d = dict(r)
        dist = None
        if lat is not None and lon is not None and d.get("latitude") and d.get("longitude"):
            d_m = _haversine_m(lat, lon, d["latitude"], d["longitude"])
            # Exclure les résultats hors rayon exact (BBox approximatif)
            if d_m > radius_km * 1000:
                total -= 1
                continue
            dist = round(d_m, 1)
        items.append(_row_to_item(d, list(d.keys()), dist))

    if lat is not None:
        items.sort(key=lambda x: x.distance_meters or float("inf"))

    return total, items


def _query_structures(db: DatabaseService, **kwargs) -> tuple[int, List[StructureItem]]:
    """Dispatch automatique PostgreSQL / SQLite."""
    if db.is_postgres:
        return _query_structures_pg(db, **kwargs)
    return _query_structures_sqlite(db, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=StructureListResponse,
    summary="Recherche multicritère dans l'Annuaire Sanitaire National",
    description="""
Filtre dynamique sur les 41 421 structures de l'annuaire national :
- **Wilaya** : par code (`code_wilaya=16`) ou nom (`nom_wilaya=Alger`)
- **Commune** : `nom_commune=Bab+El+Oued`
- **Catégorie** : `categorie=Pharmacie` ou `categorie=Établissement+Public`
- **Spécialité** : `discipline=Cardiologie`, `discipline=Chirurgien-Dentiste`
- **Recherche libre** : `q=Dr+Benmahfoud` (nom, adresse, spécialité)
- **Proximité GPS** : `lat=36.74&lon=3.06&radius_km=2` — tri par distance croissante
    """,
)
def list_structures(
    q: Optional[str] = Query(None, min_length=2, description="Recherche textuelle libre"),
    code_wilaya: Optional[str] = Query(None, min_length=2, max_length=2, description="Code wilaya (01 à 58)"),
    nom_wilaya: Optional[str] = Query(None, description="Nom de la wilaya (partiel OK)"),
    nom_commune: Optional[str] = Query(None, description="Nom de la commune (partiel OK)"),
    categorie: Optional[str] = Query(None, description="Catégorie (partiel OK : 'Pharmac', 'Clinique'…)"),
    discipline: Optional[str] = Query(None, description="Discipline/Spécialité (partiel OK : 'Cardio'…)"),
    lat: Optional[float] = Query(None, ge=18.0, le=38.5, description="Latitude GPS (Algérie)"),
    lon: Optional[float] = Query(None, ge=-9.5, le=13.0, description="Longitude GPS (Algérie)"),
    radius_km: float = Query(10.0, ge=0.1, le=200.0, description="Rayon en km (avec lat/lon)"),
    limit: int = Query(20, ge=1, le=100, description="Résultats par page"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    db: DatabaseService = Depends(get_db_service),
) -> StructureListResponse:
    t0 = time.time()

    # Validation : lat et lon doivent être fournis ensemble
    if (lat is None) != (lon is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Les paramètres `lat` et `lon` doivent être fournis ensemble.",
        )

    total, items = _query_structures(
        db,
        q=q,
        code_wilaya=code_wilaya,
        nom_wilaya=nom_wilaya,
        nom_commune=nom_commune,
        categorie=categorie,
        discipline=discipline,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        limit=limit,
        offset=offset,
    )

    return StructureListResponse(
        total=total,
        limit=limit,
        offset=offset,
        execution_time_ms=round((time.time() - t0) * 1000, 2),
        data=items,
    )


@router.get(
    "/nearby",
    response_model=StructureListResponse,
    summary="Structures à proximité immédiate (GPS)",
    description="Raccourci GPS : retourne les structures les plus proches d'un point, triées par distance.",
)
def structures_nearby(
    lat: float = Query(..., ge=18.0, le=38.5, description="Latitude de l'utilisateur"),
    lon: float = Query(..., ge=-9.5, le=13.0, description="Longitude de l'utilisateur"),
    radius_km: float = Query(5.0, ge=0.1, le=50.0, description="Rayon de recherche en km"),
    categorie: Optional[str] = Query(None, description="Filtrer par catégorie"),
    discipline: Optional[str] = Query(None, description="Filtrer par spécialité"),
    limit: int = Query(15, ge=1, le=50),
    db: DatabaseService = Depends(get_db_service),
) -> StructureListResponse:
    t0 = time.time()
    total, items = _query_structures(
        db, lat=lat, lon=lon, radius_km=radius_km,
        categorie=categorie, discipline=discipline, limit=limit, offset=0,
    )
    return StructureListResponse(
        total=total, limit=limit, offset=0,
        execution_time_ms=round((time.time() - t0) * 1000, 2),
        data=items,
    )


@router.get(
    "/{structure_id}",
    response_model=StructureItem,
    summary="Fiche détaillée d'une structure / praticien",
)
def get_structure_detail(
    structure_id: int,
    db: DatabaseService = Depends(get_db_service),
) -> StructureItem:
    if db.is_postgres:
        conn = db._get_pg_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, code_wilaya, nom_wilaya, nom_daira, nom_commune, "
                    "categorie, discipline_specialite, nom_etablissement_praticien, "
                    "adresse, telephone, horaires, latitude, longitude, "
                    "statut_remarques, source_csv, is_verified "
                    "FROM structures WHERE id = %s",
                    (structure_id,),
                )
                row = cur.fetchone()
                cols = [d[0] for d in cur.description]
        finally:
            db._release_pg_connection(conn)
    else:
        import sqlite3
        conn = sqlite3.connect(db.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                "SELECT id, code_wilaya, nom_wilaya, nom_daira, nom_commune, "
                "categorie, discipline_specialite, nom_etablissement_praticien, "
                "adresse, telephone, horaires, latitude, longitude, "
                "statut_remarques, source_csv, is_verified "
                "FROM structures WHERE id = ?",
                (structure_id,),
            )
            row = cur.fetchone()
            cols = [d[0] for d in cur.description] if cur.description else []
        finally:
            conn.close()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Structure introuvable (id={structure_id}).",
        )
    return _row_to_item(dict(zip(cols, row)), cols)


@router.get(
    "/meta/wilayas",
    response_model=List[WilayaStats],
    summary="Statistiques par wilaya (vue matérialisée)",
    description="Nombre de structures par wilaya, avec comptage GPS et catégories. "
                "Données issues de la vue matérialisée `mv_structures_par_wilaya` (PostgreSQL) "
                "ou calculées à la volée (SQLite).",
)
def stats_by_wilaya(db: DatabaseService = Depends(get_db_service)) -> List[WilayaStats]:
    if db.is_postgres:
        conn = db._get_pg_connection()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "SELECT code_wilaya, nom_wilaya, total, avec_gps, nb_categories, nb_communes "
                        "FROM mv_structures_par_wilaya ORDER BY code_wilaya"
                    )
                except Exception:
                    # Vue matérialisée pas encore créée → calcul à la volée
                    cur.execute(
                        "SELECT code_wilaya, nom_wilaya, COUNT(*) AS total, "
                        "COUNT(*) FILTER (WHERE latitude IS NOT NULL) AS avec_gps, "
                        "COUNT(DISTINCT categorie) AS nb_categories, "
                        "COUNT(DISTINCT nom_commune) AS nb_communes "
                        "FROM structures GROUP BY code_wilaya, nom_wilaya ORDER BY code_wilaya"
                    )
                rows = cur.fetchall()
        finally:
            db._return_pg_connection(conn)
    else:
        import sqlite3
        conn = sqlite3.connect(db.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(
                "SELECT code_wilaya, nom_wilaya, COUNT(*) AS total, "
                "SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) AS avec_gps, "
                "COUNT(DISTINCT categorie) AS nb_categories, "
                "COUNT(DISTINCT nom_commune) AS nb_communes "
                "FROM structures GROUP BY code_wilaya, nom_wilaya ORDER BY code_wilaya"
            )
            rows = cur.fetchall()
        finally:
            conn.close()

    return [
        WilayaStats(
            code_wilaya=r[0], nom_wilaya=r[1],
            total=r[2], avec_gps=r[3],
            nb_categories=r[4], nb_communes=r[5],
        )
        for r in rows
    ]


@router.get(
    "/meta/categories",
    response_model=List[CategorieStats],
    summary="Statistiques par catégorie sanitaire",
    description="Liste des catégories disponibles avec leur nombre de structures. "
                "Utilisé pour remplir les filtres déroulants du frontend.",
)
def stats_by_categorie(db: DatabaseService = Depends(get_db_service)) -> List[CategorieStats]:
    if db.is_postgres:
        conn = db._get_pg_connection()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        "SELECT categorie, total FROM mv_structures_par_categorie ORDER BY total DESC"
                    )
                except Exception:
                    cur.execute(
                        "SELECT categorie, COUNT(*) AS total "
                        "FROM structures GROUP BY categorie ORDER BY total DESC"
                    )
                rows = cur.fetchall()
        finally:
            db._return_pg_connection(conn)
    else:
        import sqlite3
        conn = sqlite3.connect(db.sqlite_path)
        try:
            cur = conn.execute(
                "SELECT categorie, COUNT(*) AS total "
                "FROM structures GROUP BY categorie ORDER BY total DESC"
            )
            rows = cur.fetchall()
        finally:
            conn.close()

    return [CategorieStats(categorie=r[0], total=r[1]) for r in rows]
