#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Schémas Pydantic pour l'API REST
====================================================
Validation stricte des entrées et sérialisation des sorties pour la recherche
spatiale et la contribution communautaire.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class FacilityType(str, Enum):
    CHU = "CHU"
    EPH = "EPH"
    EPSP = "EPSP"
    EHS = "EHS"
    HOPITAL = "Hôpital"
    CLINIQUE = "Clinique"
    POLYCLINIQUE = "Polyclinique"
    URGENCES = "Urgences"
    CENTRE_DE_SANTE = "Centre de Santé"
    DISPENSAIRE = "Dispensaire"
    CABINET_MEDICAL = "Cabinet Médical"


class SuggestionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class FacilityBadge(BaseModel):
    """Badge d'état pour guider l'utilisateur et inviter à la revendication professionnelle."""
    label: str = Field(..., example="Fiche informative publique")
    variant: str = Field(..., example="info", description="'info' pour non revendiqué, 'success' pour vérifié")
    is_claimed: bool = Field(..., description="Vrai si revendiqué par le personnel médical")
    is_verified: bool = Field(..., description="Vrai si les informations sont vérifiées")
    can_claim: bool = Field(..., description="Indique si un bouton de revendication doit être affiché")
    claim_url: Optional[str] = Field(None, example="/facilities/1234/claim")


class FacilityResponse(BaseModel):
    """Représentation publique d'un établissement de santé."""
    id: int
    name: str
    type: str
    wilaya: str
    wilaya_code: Optional[str] = None
    commune: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: float
    longitude: float
    is_claimed: bool
    is_verified: bool
    source: str
    google_place_id: Optional[str] = None
    osm_id: Optional[str] = None
    distance_meters: Optional[float] = Field(None, description="Distance au point de recherche en mètres")
    badge: FacilityBadge
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class FacilitySearchQuery(BaseModel):
    """Paramètres de recherche géospatiale et textuelle."""
    lat: Optional[float] = Field(None, ge=18.0, le=38.5, description="Latitude WGS84")
    lon: Optional[float] = Field(None, ge=-9.5, le=13.0, description="Longitude WGS84")
    radius_km: float = Field(10.0, ge=0.05, le=100.0, description="Rayon de recherche en km")
    
    # Bounding Box pour affichage direct sur carte interactive
    min_lat: Optional[float] = Field(None, ge=18.0, le=38.5)
    min_lon: Optional[float] = Field(None, ge=-9.5, le=13.0)
    max_lat: Optional[float] = Field(None, ge=18.0, le=38.5)
    max_lon: Optional[float] = Field(None, ge=-9.5, le=13.0)

    # Filtres métiers
    type: Optional[FacilityType] = None
    wilaya: Optional[str] = None
    commune: Optional[str] = None
    q: Optional[str] = Field(None, min_length=2, description="Recherche textuelle libre")
    is_claimed: Optional[bool] = Field(None, description="None = Tous, False = Fiches publiques, True = Revendiqués")

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class FacilitySearchListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[FacilityResponse]
    execution_time_ms: float


class SuggestFacilityRequest(BaseModel):
    """Formulaire de contribution citoyenne / professionnelle pour établissement manquant."""
    name: str = Field(..., min_length=3, max_length=255, example="Polyclinique El Biar")
    type: Optional[FacilityType] = Field(FacilityType.POLYCLINIQUE, example="Polyclinique")
    wilaya: str = Field(..., min_length=2, max_length=100, example="Alger")
    commune: Optional[str] = Field(None, max_length=100, example="El Biar")
    address: Optional[str] = Field(None, example="12 Rue Ali Khodja")
    phone: Optional[str] = Field(None, example="021 92 00 00")
    
    latitude: Optional[float] = Field(None, ge=18.0, le=38.5)
    longitude: Optional[float] = Field(None, ge=-9.5, le=13.0)
    google_maps_url: Optional[str] = Field(
        None,
        example="https://maps.google.com/?q=36.7682,3.0315",
        description="Lien de partage Google Maps ou fiche Google",
    )

    submitter_name: Optional[str] = Field(None, max_length=150, example="Dr. Amine B.")
    submitter_email: Optional[str] = Field(None, max_length=150, example="amine@example.com")
    submitter_phone: Optional[str] = Field(None, max_length=50, example="0550 12 34 56")
    submitter_notes: Optional[str] = Field(None, max_length=1000, example="Structure ouverte 24h/24 avec service de radiologie.")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Le nom de l'établissement doit comporter au moins 3 caractères.")
        return cleaned


class SuggestFacilityResponse(BaseModel):
    suggestion_id: int
    status: SuggestionStatus
    message: str
    parsed_coordinates: Optional[Dict[str, float]] = None
    possible_duplicate_facility_id: Optional[int] = None
    created_at: datetime


class SuggestionDetailResponse(BaseModel):
    """Fiche détaillée d'une suggestion citoyenne pour l'interface de modération."""
    id: int
    name: str
    type: Optional[str] = None
    wilaya: str
    commune: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_url: Optional[str] = None
    submitter_name: Optional[str] = None
    submitter_email: Optional[str] = None
    submitter_phone: Optional[str] = None
    submitter_notes: Optional[str] = None
    status: SuggestionStatus
    matched_facility_id: Optional[int] = None
    potential_duplicate: Optional[FacilityResponse] = None
    moderated_by: Optional[str] = None
    moderated_at: Optional[datetime] = None
    moderation_comment: Optional[str] = None
    created_at: Optional[datetime] = None


class SuggestionListResponse(BaseModel):
    total: int
    status_filter: Optional[str] = None
    data: List[SuggestionDetailResponse]


class ApproveSuggestionRequest(BaseModel):
    """Paramètres d'approbation administrative d'une suggestion."""
    moderator_name: Optional[str] = Field("Admin MEDIZY", example="Dr. Responsable DSP")
    override_name: Optional[str] = Field(None, example="CHU Mustapha Bacha (Orthopédie)")
    override_type: Optional[FacilityType] = None
    override_address: Optional[str] = None
    override_phone: Optional[str] = None
    moderation_comment: Optional[str] = Field(None, example="Structure vérifiée auprès du registre sanitaire.")


class ApproveSuggestionResponse(BaseModel):
    suggestion_id: int
    status: SuggestionStatus
    created_facility_id: int
    facility: FacilityResponse
    message: str


class RejectSuggestionRequest(BaseModel):
    """Paramètres de rejet motivé d'une suggestion."""
    reason: str = Field(..., min_length=3, max_length=500, example="Établissement fermé définitivement ou informations erronées")
    moderator_name: Optional[str] = Field("Admin MEDIZY", example="Modérateur Régional")


class RejectSuggestionResponse(BaseModel):
    suggestion_id: int
    status: SuggestionStatus
    reason: str
    message: str


class AdminLoginRequest(BaseModel):
    """Identifiants de connexion administrateur."""
    username: str = Field(..., example="admin@medizy.dz")
    password: str = Field(..., example="MedizyAdmin2026!")


class AdminTokenResponse(BaseModel):
    """Jeton d'accès JWT sécurisé retourné après authentification réussie."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(86400, description="Durée de validité en secondes (24 heures)")
    admin_name: str
    role: str


class FacilityExportItem(BaseModel):
    """Structure légère optimisée pour l'index sémantique et la vectorisation de NIBRAS."""
    id: int
    name: str
    type: str
    wilaya: str
    wilaya_code: Optional[str] = None
    commune: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: float
    longitude: float
    is_claimed: bool
    is_verified: bool
    source: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    embedding_context: str = Field(
        ...,
        description="Chunk textuel synthétique prêt à être vectorisé par le LLM NIBRAS pour le RAG.",
    )


class FacilityExportResponse(BaseModel):
    """Réponse paginée par curseur pour la synchronisation externe continue."""
    count: int
    has_more: bool
    next_cursor: Optional[str] = None
    sync_timestamp: str
    facilities: List[FacilityExportItem]
