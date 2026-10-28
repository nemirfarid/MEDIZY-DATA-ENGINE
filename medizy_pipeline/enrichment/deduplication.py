#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Moteur de Déduplication Géospatiale et Sémantique
=====================================================================
Détecte les doublons entre les données ingérées (OSM, Google Places) et
le référentiel existant selon deux critères conjoints :
  1. Distance spatiale inférieure à 100 mètres (Haversine ou PostGIS ST_DWithin)
  2. Similarité textuelle sur les noms normalisés (Jaccard + Levenshtein / SequenceMatcher)
"""

import math
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from .classifier import normalize_text

# Mots vides médicaux et toponymiques fréquents à ignorer lors du calcul de similarité
STOP_WORDS = {
    "clinique", "hopital", "hospital", "centre", "cabinet", "dr", "docteur",
    "eph", "epsp", "chu", "ehs", "polyclinique", "dispensaire", "urgences",
    "sante", "medical", "algerie", "alger", "el", "al", "de", "du", "des",
    "et", "la", "le", "les", "d", "l", "medecin", "specialise", "service"
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance géodésique en mètres entre deux points GPS (WGS84).
    Précision suffisante pour le filtrage de proximité métrique (< 100m).
    """
    R = 6371000.0  # Rayon moyen de la Terre en mètres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def get_core_tokens(text: str) -> set:
    """Extrait les tokens significatifs du nom en éliminant les stop words génériques."""
    norm = normalize_text(text)
    tokens = set(norm.split())
    meaningful = tokens - STOP_WORDS
    return meaningful if meaningful else tokens


def compute_name_similarity(name1: str, name2: str) -> float:
    """
    Score combiné de similarité de noms (0.0 à 1.0) combinant :
      - Jaccard similarity sur les tokens discriminants (noms de médecins, lieux-dits, saints, etc.)
      - SequenceMatcher ratio sur la chaîne globale nettoyée.
    """
    if not name1 or not name2:
        return 0.0

    s1 = normalize_text(name1)
    s2 = normalize_text(name2)

    if s1 == s2:
        return 1.0

    # 1. Similarité globale de séquence
    seq_ratio = SequenceMatcher(None, s1, s2).ratio()

    # 2. Similarité Jaccard sur les tokens porteurs de sens
    tokens1 = get_core_tokens(name1)
    tokens2 = get_core_tokens(name2)

    if not tokens1 or not tokens2:
        return seq_ratio

    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    jaccard_ratio = intersection / union if union > 0 else 0.0

    # Coefficient de confinement (Overlap / Simpson) : si le nom court est totalement contenu dans le nom long
    min_tokens = min(len(tokens1), len(tokens2))
    containment = (intersection / min_tokens) if min_tokens > 0 else 0.0

    # Si au moins un mot-clé distinctif est partagé (ex: "azhar", "hassan", "benboulaid")
    shared_length = sum(len(t) for t in (tokens1 & tokens2))
    if containment >= 0.80 and shared_length >= 4:
        jaccard_ratio = max(jaccard_ratio, 0.85)
    elif shared_length >= 4 and intersection >= 1:
        jaccard_ratio = max(jaccard_ratio, 0.75)

    return max(seq_ratio, jaccard_ratio)


def is_duplicate_match(
    cand_lat: float,
    cand_lon: float,
    cand_name: str,
    cand_google_id: Optional[str],
    cand_osm_id: Optional[str],
    existing_facility: Dict,
    max_distance_meters: float = 100.0,
    min_similarity: float = 0.68,
) -> Tuple[bool, float, float, str]:
    """
    Évalue si un candidat correspond à un établissement existant.
    
    Retourne :
      (is_match: bool, distance_m: float, similarity: float, match_reason: str)
    """
    # 1. Correspondance exacte sur identifiant externe
    if cand_google_id and existing_facility.get("google_place_id") == cand_google_id:
        return True, 0.0, 1.0, "EXACT_GOOGLE_PLACE_ID"

    if cand_osm_id and existing_facility.get("osm_id") == cand_osm_id:
        return True, 0.0, 1.0, "EXACT_OSM_ID"

    ex_lat = existing_facility.get("latitude")
    ex_lon = existing_facility.get("longitude")

    if cand_lat is None or cand_lon is None or ex_lat is None or ex_lon is None:
        return False, -1.0, 0.0, "MISSING_COORDINATES"

    # 2. Calcul de la distance géodésique
    dist = haversine_distance_meters(cand_lat, cand_lon, ex_lat, ex_lon)

    if dist > max_distance_meters:
        return False, dist, 0.0, "OUT_OF_SPATIAL_RADIUS"

    # 3. Calcul de similarité du nom
    sim = compute_name_similarity(cand_name, existing_facility.get("name", ""))

    # Règle A : Même emplacement immédiat (< 25 mètres) et similarité modérée (> 0.50)
    if dist <= 25.0 and sim >= 0.50:
        return True, dist, sim, f"HIGH_PROXIMITY_MATCH ({dist:.1f}m, sim: {sim:.2f})"

    # Règle B : Dans le rayon de 100 mètres et similarité textuelle confirmée
    if dist <= max_distance_meters and sim >= min_similarity:
        return True, dist, sim, f"GEO_NAME_MATCH ({dist:.1f}m, sim: {sim:.2f})"

    return False, dist, sim, "NO_MATCH"
