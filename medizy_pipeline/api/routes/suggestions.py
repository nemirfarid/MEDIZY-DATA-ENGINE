#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Endpoints de Contribution Communautaire (Crowdsourcing)
==========================================================================
Permet aux citoyens, médecins et administrateurs de suggérer des structures manquantes
via coordonnées directes ou lien Google Maps, avec extraction intelligente et modération.
"""

import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status

from ..db import DatabaseService, get_db_service
from ..schemas import (
    SuggestFacilityRequest,
    SuggestFacilityResponse,
    SuggestionStatus,
)
from ...enrichment.classifier import normalize_algerian_phone
from ...enrichment.url_parser import extract_coordinates_from_url

logger = logging.getLogger("medizy.api.suggestions")

router = APIRouter(prefix="/api/v1/facilities", tags=["Contributions Communautaires"])


@router.post(
    "/suggest",
    response_model=SuggestFacilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Suggérer un établissement de santé manquant",
    description="""
    Permet à un utilisateur ou praticien de proposer un établissement absent du répertoire :
    - Soit en fournissant les coordonnées GPS (`latitude`, `longitude`).
    - Soit en fournissant un lien Google Maps (les coordonnées sont extraites automatiquement).
    - Un contrôle de déduplication immédiat (< 100m) est exécuté pour alerter l'équipe de modération.
    - La suggestion est stockée dans la table de modération avec le statut `PENDING`.
    """,
)
def suggest_facility(
    payload: SuggestFacilityRequest,
    db: DatabaseService = Depends(get_db_service),
):
    lat = payload.latitude
    lon = payload.longitude

    # 1. Extraction automatique des coordonnées depuis le lien Google Maps si nécessaire
    if (lat is None or lon is None) and payload.google_maps_url:
        extracted_lat, extracted_lon = extract_coordinates_from_url(payload.google_maps_url)
        if extracted_lat is not None and extracted_lon is not None:
            lat, lon = extracted_lat, extracted_lon
            logger.info(f"Coordonnées extraites avec succès de l'URL Google Maps: ({lat}, {lon})")

    # Si aucune coordonnée n'a pu être déterminée, validation de cohérence
    if lat is None or lon is None:
        if not payload.address and not payload.google_maps_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Veuillez fournir soit des coordonnées GPS, soit une adresse précise, soit un lien Google Maps valide.",
            )

    # 2. Normalisation du numéro de téléphone
    phone_e164, phone_disp = normalize_algerian_phone(payload.phone)

    # 3. Pré-détection de doublon géospatial (< 100m)
    potential_duplicate_id = None
    if lat is not None and lon is not None:
        potential_duplicate_id = db.find_potential_duplicate(
            name=payload.name,
            lat=lat,
            lon=lon,
            wilaya=payload.wilaya,
        )

    # 4. Enregistrement en base de modération
    suggestion_id = db.insert_suggestion(
        name=payload.name,
        facility_type=payload.type.value if payload.type else None,
        wilaya=payload.wilaya,
        commune=payload.commune,
        address=payload.address,
        phone=phone_disp or payload.phone,
        lat=lat,
        lon=lon,
        google_maps_url=payload.google_maps_url,
        submitter_name=payload.submitter_name,
        submitter_email=payload.submitter_email,
        submitter_phone=payload.submitter_phone,
        submitter_notes=payload.submitter_notes,
        matched_facility_id=potential_duplicate_id,
    )

    msg = "Votre suggestion a été enregistrée avec succès et sera validée par l'équipe MEDIZY."
    if potential_duplicate_id:
        msg += " Note : Un établissement similaire a été repéré à proximité et sera comparé lors de la modération."

    return SuggestFacilityResponse(
        suggestion_id=suggestion_id,
        status=SuggestionStatus.PENDING,
        message=msg,
        parsed_coordinates={"latitude": lat, "longitude": lon} if (lat and lon) else None,
        possible_duplicate_facility_id=potential_duplicate_id,
        created_at=datetime.now(timezone.utc),
    )
