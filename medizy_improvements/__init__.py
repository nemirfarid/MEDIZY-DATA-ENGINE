# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Package d'amélioration du scraping
=======================================================
Modules :
- normalization : normalisation *_raw / *_normalized
- deduplication : dédoublonage multi-niveaux avec seuils de confiance
- data_quality : métriques de qualité
- taxonomie_specialites : vocabulaire contrôlé des spécialités
- communes_algerie : architecture communes/wilayas pour couverture nationale
"""

try:
    from .normalization import apply_normalization, normalize_phone_raw, normalize_text, normalize_wilaya
    from .deduplication import DeduplicationEngine, merge_rows, confidence_level
    from .data_quality import DataQualityChecker
    from .taxonomie_specialites import SPECIALITES, get_specialite_by_code, normalize_specialite, build_search_variants
    from .communes_algerie import WILAYAS, COMMUNES_BY_WILAYA, DENSITY, get_communes, get_density, build_wilaya_commune_queries
except (ImportError, ModuleNotFoundError):
    try:
        from normalization import apply_normalization, normalize_phone_raw, normalize_text, normalize_wilaya
        from deduplication import DeduplicationEngine, merge_rows, confidence_level
        from data_quality import DataQualityChecker
        from taxonomie_specialites import SPECIALITES, get_specialite_by_code, normalize_specialite, build_search_variants
        from communes_algerie import WILAYAS, COMMUNES_BY_WILAYA, DENSITY, get_communes, get_density, build_wilaya_commune_queries
    except (ImportError, ModuleNotFoundError):
        pass

__all__ = [
    "apply_normalization",
    "normalize_phone_raw",
    "normalize_text",
    "normalize_wilaya",
    "DeduplicationEngine",
    "merge_rows",
    "confidence_level",
    "DataQualityChecker",
    "SPECIALITES",
    "get_specialite_by_code",
    "normalize_specialite",
    "build_search_variants",
    "WILAYAS",
    "COMMUNES_BY_WILAYA",
    "DENSITY",
    "get_communes",
    "get_density",
    "build_wilaya_commune_queries",
]
