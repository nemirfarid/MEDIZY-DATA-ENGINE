#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Endpoints de Recherche Géospatiale & Établissements
======================================================================
Recherche spatiale (Rayon R / Bounding Box), filtres multicritères et affichage
transparent des fiches publiques non revendiquées avec badge dédié.
"""

import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..db import DatabaseService, get_db_service
from ..schemas import (
    FacilityExportResponse,
    FacilityResponse,
    FacilitySearchListResponse,
    FacilitySearchQuery,
    FacilityType,
)

router = APIRouter(prefix="/api/v1/facilities", tags=["Établissements de Santé"])


@router.get(
    "/search",
    response_model=FacilitySearchListResponse,
    summary="Recherche géospatiale et multicritère d'établissements",
    description="""
    Recherche hautement optimisée pour la carte interactive et le moteur de recherche :
    - **Proximité GPS** : spécifier `lat`, `lon` et `radius_km` pour un tri par distance exacte.
    - **Bounding Box** : spécifier `min_lat`, `min_lon`, `max_lat`, `max_lon` pour le viewport cartographique.
    - **Inclusion totale** : les fiches non encore revendiquées (`is_claimed = false`) sont incluses par défaut avec un badge informatif public.
    - **Filtres administratifs** : filtrer par `type` (CHU, EPH, EPSP, Clinique, Polyclinique, etc.) et par `wilaya`.
    """,
)
def search_facilities(
    lat: Optional[float] = Query(None, ge=18.0, le=38.5, description="Latitude WGS84 du centre"),
    lon: Optional[float] = Query(None, ge=-9.5, le=13.0, description="Longitude WGS84 du centre"),
    radius_km: float = Query(10.0, ge=0.05, le=100.0, description="Rayon en kilomètres autour du point"),
    min_lat: Optional[float] = Query(None, ge=18.0, le=38.5, description="BBox Sud"),
    min_lon: Optional[float] = Query(None, ge=-9.5, le=13.0, description="BBox Ouest"),
    max_lat: Optional[float] = Query(None, ge=18.0, le=38.5, description="BBox Nord"),
    max_lon: Optional[float] = Query(None, ge=-9.5, le=13.0, description="BBox Est"),
    type: Optional[FacilityType] = Query(None, description="Typologie (CHU, EPH, EPSP, Clinique, Polyclinique...)"),
    wilaya: Optional[str] = Query(None, description="Nom officiel ou code de wilaya (01 à 58)"),
    commune: Optional[str] = Query(None, description="Nom de commune"),
    q: Optional[str] = Query(None, min_length=2, description="Recherche plein texte par nom ou adresse"),
    is_claimed: Optional[bool] = Query(
        None, description="Statut de revendication : None = Tous (recommandé), true = vérifiés, false = publics"
    ),
    limit: int = Query(20, ge=1, le=100, description="Nombre de résultats par page"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    db: DatabaseService = Depends(get_db_service),
):
    start = time.time()

    search_query = FacilitySearchQuery(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        type=type,
        wilaya=wilaya,
        commune=commune,
        q=q,
        is_claimed=is_claimed,
        limit=limit,
        offset=offset,
    )

    total, items = db.search_facilities(search_query)
    elapsed = time.time() - start
    elapsed_ms = elapsed * 1000.0

    try:
        from ..metrics import record_geosearch_metrics
        record_geosearch_metrics("/search", elapsed, type_filter=type, wilaya=wilaya)
    except Exception:
        pass

    return FacilitySearchListResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=items,
        execution_time_ms=round(elapsed_ms, 2),
    )


@router.get(
    "/nearby",
    response_model=FacilitySearchListResponse,
    summary="Recherche rapide de proximité GPS",
    description="Raccourci spatial retournant les structures les plus proches d'une position GPS donnée.",
)
def get_nearby_facilities(
    lat: float = Query(..., ge=18.0, le=38.5, description="Latitude utilisateur"),
    lon: float = Query(..., ge=-9.5, le=13.0, description="Longitude utilisateur"),
    radius_km: float = Query(5.0, ge=0.05, le=50.0, description="Rayon de proximité (défaut 5 km)"),
    type: Optional[FacilityType] = Query(None, description="Filtrer par type"),
    limit: int = Query(15, ge=1, le=50),
    db: DatabaseService = Depends(get_db_service),
):
    start = time.time()
    search_query = FacilitySearchQuery(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        type=type,
        limit=limit,
        offset=0,
    )
    total, items = db.search_facilities(search_query)
    elapsed = time.time() - start
    elapsed_ms = elapsed * 1000.0

    try:
        from ..metrics import record_geosearch_metrics
        record_geosearch_metrics("/nearby", elapsed, type_filter=type, wilaya="gps_point")
    except Exception:
        pass

    return FacilitySearchListResponse(
        total=total,
        limit=limit,
        offset=0,
        data=items,
        execution_time_ms=round(elapsed_ms, 2),
    )


@router.get(
    "/export/latest",
    response_model=FacilityExportResponse,
    summary="Passerelle de synchronisation externe (Index sémantique NIBRAS)",
    description="""
    Permet à l'agent conversationnel NIBRAS et aux services externes de maintenir
    un index vectoriel/sémantique local à jour via pagination par curseur strictly monotone
    et filtrage temporel par `updated_since`.
    """,
)
def export_latest_facilities(
    cursor: Optional[int] = Query(None, description="Curseur de pagination (ID du dernier élément traité)"),
    limit: int = Query(100, ge=1, le=500, description="Nombre de fiches par lot (max 500)"),
    updated_since: Optional[str] = Query(None, description="Filtre ISO 8601 pour les modifications récentes"),
    wilaya: Optional[str] = Query(None, description="Filtrer par wilaya cible"),
    db: DatabaseService = Depends(get_db_service),
):
    import datetime
    start = time.time()
    items, has_more, next_cursor = db.export_facilities_incremental(
        cursor=cursor,
        updated_since=updated_since,
        wilaya=wilaya,
        limit=limit,
    )

    try:
        from ..metrics import nibras_sync_exports_total
        nibras_sync_exports_total.labels(status="success").inc()
    except Exception:
        pass

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return FacilityExportResponse(
        count=len(items),
        has_more=has_more,
        next_cursor=next_cursor,
        sync_timestamp=now_iso,
        facilities=items,
    )


@router.get(
    "/{facility_id}",
    response_model=FacilityResponse,
    summary="Fiche détaillée d'un établissement de santé",
)
def get_facility_detail(facility_id: int, db: DatabaseService = Depends(get_db_service)):
    facility = db.get_facility_by_id(facility_id)
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Établissement avec l'identifiant {facility_id} introuvable.",
        )
    return facility
