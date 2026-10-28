#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Back-Office & Modération des Suggestions Citoyennes
=======================================================================
Module sécurisé avec authentification par jeton JWT et limitation de débit :
- Authentification avec expiration via `POST /api/v1/admin/auth/login`.
- Protection anti-brute force via le RateLimiter Redis / in-memory.
- Consultation des fiches suggérées avec détection de doublons (< 100m).
- Approbation (insertion dans `facilities` avec `source='community_suggestion'`).
- Rejet motivé avec traçabilité administrative.
"""

import logging
import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..db import DatabaseService, get_db_service
from ..rate_limiter import admin_action_rate_limiter, login_rate_limiter
from ..schemas import (
    AdminLoginRequest,
    AdminTokenResponse,
    ApproveSuggestionRequest,
    ApproveSuggestionResponse,
    RejectSuggestionRequest,
    RejectSuggestionResponse,
    SuggestionDetailResponse,
    SuggestionListResponse,
    SuggestionStatus,
)
from ..security import (
    create_access_token,
    get_current_admin,
    verify_admin_credentials,
)

logger = logging.getLogger("medizy.api.admin")

router = APIRouter(prefix="/api/v1/admin", tags=["Back-Office & Modération Administrative"])


@router.post(
    "/auth/login",
    response_model=AdminTokenResponse,
    summary="Authentification administrateur et délivrance du jeton JWT",
    description="""
    Point d'entrée sécurisé pour les modérateurs et directeurs de la santé (DSP) :
    - Vérification en temps constant des identifiants (protection anti-timing).
    - Protection stricte anti-force brute par limitation de débit (5 tentatives/minute).
    - Génération d'un jeton Bearer JWT signé avec expiration à 24 heures.
    """,
    dependencies=[Depends(login_rate_limiter)],
)
def admin_login(payload: AdminLoginRequest):
    """Authentifie l'administrateur et délivre le jeton Bearer JWT."""
    if not verify_admin_credentials(payload.username, payload.password):
        logger.warning(f"Échec de connexion administrateur pour l'utilisateur '{payload.username}'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects (nom d'utilisateur ou mot de passe invalide).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Création du jeton JWT sécurisé
    token = create_access_token(
        subject=payload.username,
        name="Administrateur MEDIZY",
        role="superadmin",
    )
    logger.info(f"Authentification réussie pour '{payload.username}'. Jeton JWT délivré.")

    return AdminTokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=86400,
        admin_name="Administrateur MEDIZY",
        role="superadmin",
    )


@router.get(
    "/suggestions",
    response_model=SuggestionListResponse,
    summary="Lister les contributions citoyennes à modérer",
    description="""
    Retourne la liste des établissements proposés par les citoyens et professionnels :
    - Requiert une authentification Bearer JWT valide (ou clé API système).
    - Filtrage par statut (`PENDING`, `APPROVED`, `REJECTED`, `ALL`).
    - Chaque fiche inclut la détection de doublon potentiel pour vérification comparative cartographique.
    """,
    dependencies=[Depends(admin_action_rate_limiter)],
)
def get_pending_suggestions(
    status_filter: Optional[str] = Query(
        "PENDING",
        alias="status",
        description="Filtre de statut : PENDING (défaut), APPROVED, REJECTED, ALL",
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: DatabaseService = Depends(get_db_service),
):
    total, items = db.list_suggestions(status_filter=status_filter, limit=limit, offset=offset)
    return SuggestionListResponse(
        total=total,
        status_filter=status_filter,
        data=[SuggestionDetailResponse(**item) for item in items],
    )


@router.post(
    "/suggestions/{suggestion_id}/approve",
    response_model=ApproveSuggestionResponse,
    summary="Approuver une suggestion et l'intégrer au répertoire national",
    description="""
    Valide une suggestion citoyenne :
    1. Crée la structure dans la table principale `facilities` (`source = 'community_suggestion'`, `is_verified = true`).
    2. Marque la suggestion comme `APPROVED` avec l'identité de l'administrateur connecté.
    """,
    dependencies=[Depends(admin_action_rate_limiter)],
)
def approve_suggestion_endpoint(
    suggestion_id: int,
    payload: Optional[ApproveSuggestionRequest] = None,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: DatabaseService = Depends(get_db_service),
):
    req = payload or ApproveSuggestionRequest()
    moderator = req.moderator_name or current_admin.get("name", "Admin MEDIZY")
    try:
        overrides = {
            "name": req.override_name,
            "type": req.override_type.value if req.override_type else None,
            "address": req.override_address,
            "phone": req.override_phone,
        }
        facility, updated_sugg = db.approve_suggestion(
            suggestion_id=suggestion_id,
            moderator_name=moderator,
            comment=req.moderation_comment,
            overrides={k: v for k, v in overrides.items() if v is not None},
        )
        logger.info(f"Suggestion {suggestion_id} approuvée par '{moderator}'. Structure créée ID {facility.id}.")

        return ApproveSuggestionResponse(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.APPROVED,
            created_facility_id=facility.id,
            facility=facility,
            message=f"Établissement '{facility.name}' approuvé et intégré avec succès au répertoire public MEDIZY.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de l'approbation de la suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors de la validation : {e}",
        )


@router.post(
    "/suggestions/{suggestion_id}/reject",
    response_model=RejectSuggestionResponse,
    summary="Rejeter une suggestion avec motif",
    description="""
    Rejette une suggestion citoyenne avec motif explicite (doublon avéré, fermeture définitive, spam).
    La suggestion passe au statut `REJECTED`.
    """,
    dependencies=[Depends(admin_action_rate_limiter)],
)
def reject_suggestion_endpoint(
    suggestion_id: int,
    payload: RejectSuggestionRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: DatabaseService = Depends(get_db_service),
):
    moderator = payload.moderator_name or current_admin.get("name", "Admin MEDIZY")
    try:
        updated_sugg = db.reject_suggestion(
            suggestion_id=suggestion_id,
            reason=payload.reason,
            moderator_name=moderator,
        )
        logger.info(f"Suggestion {suggestion_id} rejetée par '{moderator}'. Motif : '{payload.reason}'.")
        return RejectSuggestionResponse(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.REJECTED,
            reason=payload.reason,
            message="La suggestion a été rejetée avec succès.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors du rejet de la suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne lors du rejet : {e}",
        )
