# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Module d'intégration des améliorations
==========================================================
Ce module expose les fonctionnalités avancées sans modifier le scraper principal.

Il permet :
- normalisation des données
- déduplication avec scoring
- analyse de couverture
- enrichissement des fiches
- accès au référentiel officiel des communes
- génération de rapports

Toutes les opérations sont non destructives et fonctionnent sur des copies.
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent

# Imports des modules d'amélioration
from normalization import apply_normalization, normalize_phone_raw, normalize_text, normalize_wilaya
from deduplication import DeduplicationEngine, compute_similarity_score, merge_rows, AUTO_MERGE_THRESHOLD, CANDIDATE_THRESHOLD
from data_quality import DataQualityChecker
from coverage_analyzer import CoverageAnalyzer
from taxonomie_specialites import SPECIALITES, get_specialite_by_code, normalize_specialite, build_search_variants
from communes_officielles import (
    get_communes_by_wilaya,
    get_all_communes,
    get_commune_by_name,
    get_commune_by_zip,
    detect_commune_from_address,
    build_wilaya_commune_queries,
)
from communes_algerie import WILAYAS, COMMUNES_BY_WILAYA, DENSITY, get_communes, get_density

__all__ = [
    "apply_normalization",
    "normalize_phone_raw",
    "normalize_text",
    "normalize_wilaya",
    "DeduplicationEngine",
    "compute_similarity_score",
    "merge_rows",
    "AUTO_MERGE_THRESHOLD",
    "CANDIDATE_THRESHOLD",
    "DataQualityChecker",
    "CoverageAnalyzer",
    "SPECIALITES",
    "get_specialite_by_code",
    "normalize_specialite",
    "build_search_variants",
    "get_communes_by_wilaya",
    "get_all_communes",
    "get_commune_by_name",
    "get_commune_by_zip",
    "detect_commune_from_address",
    "build_wilaya_commune_queries",
    "WILAYAS",
    "COMMUNES_BY_WILAYA",
    "DENSITY",
    "get_communes",
    "get_density",
]
