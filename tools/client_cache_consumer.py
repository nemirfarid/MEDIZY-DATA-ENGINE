#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Consommateur Client Mobile de Référence (Phase 5)
=====================================================================
Démontre le fonctionnement hors-ligne (offline-first) d'un terminal mobile :
1. Chargement et décompression en mémoire du cache national GZIP.
2. Indexation inversée en mémoire vive (RAM) pour recherches sub-milliseconde.
3. Exécution des requêtes types avec mesure de latence (objectif : < 15 ms).
"""

import argparse
import gzip
import json
import os
import sys
import time
import unicodedata
from typing import Any, Dict, List, Optional, Set

DEFAULT_CACHE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "exports", "mobile", "medizy_national_cache.json.gz")
)


def strip_accents(text: str) -> str:
    """Normalise une chaîne de caractères pour la recherche insensible."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip().replace("-", " ").replace("'", " ")


class MemoryCacheSearcher:
    """Moteur de recherche local optimisé avec index inversé en mémoire vive."""

    def __init__(self, facilities: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None):
        self.facilities = facilities
        self.metadata = metadata or {}
        
        # Structures d'indexation ultra-rapide
        self._by_wilaya: Dict[str, List[int]] = {}
        self._by_category: Dict[str, List[int]] = {}
        self._token_index: Dict[str, List[int]] = {}
        self._indexed_records: List[Dict[str, str]] = []

        for idx, f in enumerate(facilities):
            w_norm = strip_accents(f.get("wil") or "")
            c_norm = strip_accents(f.get("com") or "")
            cat_norm = strip_accents(f.get("cat") or "")
            nom_norm = strip_accents(f.get("nom") or "")
            adr_norm = strip_accents(f.get("adr") or "")
            full_text = f"{nom_norm} {cat_norm} {w_norm} {c_norm} {adr_norm}"

            self._indexed_records.append({
                "w": w_norm,
                "c": c_norm,
                "cat": cat_norm,
                "full_text": full_text
            })

            # Indexation par clé exacte
            if w_norm:
                self._by_wilaya.setdefault(w_norm, []).append(idx)
            if cat_norm:
                self._by_category.setdefault(cat_norm, []).append(idx)

            # Index inversé par token (mots de >= 2 caractères)
            tokens: Set[str] = set(full_text.split())
            for tok in tokens:
                if len(tok) >= 2:
                    self._token_index.setdefault(tok, []).append(idx)

    @classmethod
    def load_from_gzip(cls, cache_path: str = DEFAULT_CACHE_PATH) -> "MemoryCacheSearcher":
        """Décompresse et charge l'archive GZIP en mémoire."""
        if not os.path.exists(cache_path):
            raise FileNotFoundError(f"Fichier de cache introuvable : {cache_path}")
        with gzip.open(cache_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        return cls(facilities=data.get("facilities", []), metadata=data.get("metadata", {}))

    def search(
        self,
        query: Optional[str] = None,
        wilaya: Optional[str] = None,
        commune: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Recherche multicritère instantanée avec intersection d'index inversés."""
        t0 = time.perf_counter()

        q_norm = strip_accents(query) if query else None
        w_norm = strip_accents(wilaya) if wilaya else None
        com_norm = strip_accents(commune) if commune else None
        cat_norm = strip_accents(category) if category else None

        candidate_sets: List[Set[int]] = []

        # 1. Pré-filtrage par Wilaya
        if w_norm:
            wil_matches = set()
            for key, indices in self._by_wilaya.items():
                if w_norm in key:
                    wil_matches.update(indices)
            candidate_sets.append(wil_matches)

        # 2. Pré-filtrage par Catégorie
        if cat_norm:
            cat_matches = set()
            for key, indices in self._by_category.items():
                if cat_norm in key:
                    cat_matches.update(indices)
            candidate_sets.append(cat_matches)

        # 3. Pré-filtrage par Mots-clés / Commune via index inversé
        tokens_to_filter = []
        if com_norm:
            tokens_to_filter.extend(com_norm.split())
        if q_norm:
            tokens_to_filter.extend(q_norm.split())

        for tok in tokens_to_filter:
            if len(tok) >= 2:
                matched_token_indices = set(self._token_index.get(tok, []))
                candidate_sets.append(matched_token_indices)

        # 4. Intersection optimale des ensembles de candidats
        if candidate_sets:
            # Trier par taille croissante pour minimiser les opérations d'intersection
            candidate_sets.sort(key=len)
            candidate_indices = set(candidate_sets[0])
            for s in candidate_sets[1:]:
                candidate_indices.intersection_update(s)
                if not candidate_indices:
                    break
        else:
            candidate_indices = range(len(self.facilities))

        # 5. Filtrage fin et pagination
        matched = []
        for idx in candidate_indices:
            item = self._indexed_records[idx]
            if w_norm and w_norm not in item["w"]:
                continue
            if com_norm and com_norm not in item["c"] and com_norm not in item["full_text"]:
                continue
            if cat_norm and cat_norm not in item["cat"]:
                continue
            if q_norm and q_norm not in item["full_text"]:
                continue
            matched.append(self.facilities[idx])
            if len(matched) >= limit:
                break

        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0

        return {
            "query": query,
            "wilaya": wilaya,
            "commune": commune,
            "category": category,
            "total_matches": len(matched),
            "elapsed_ms": round(elapsed_ms, 3),
            "results": matched
        }


def run_benchmark(cache_path: str = DEFAULT_CACHE_PATH) -> Dict[str, Any]:
    """Exécute les 3 requêtes de référence et retourne les métriques."""
    t0_load = time.perf_counter()
    searcher = MemoryCacheSearcher.load_from_gzip(cache_path)
    t1_load = time.perf_counter()
    load_time_ms = round((t1_load - t0_load) * 1000.0, 2)

    # Échauffement préalable de la mémoire et des caches de boucle
    searcher.search(wilaya="Alger", limit=5)
    searcher.search(query="hopital", limit=5)

    # 1. Requête type 1 : "cardiologue" à Oran
    q1 = searcher.search(wilaya="Oran", category="cardiologue", limit=10)

    # 2. Requête type 2 : "pharmacie" à Sidi Ali (Mostaganem)
    q2 = searcher.search(commune="Sidi Ali", category="pharmacie", limit=10)

    # 3. Requête type 3 : urgences / clinique de nuit
    q3 = searcher.search(query="clinique", limit=10)

    benchmarks = [
        {"name": "Recherche 'cardiologue' à Oran", "metrics": q1},
        {"name": "Recherche 'pharmacie' à Sidi Ali", "metrics": q2},
        {"name": "Recherche 'clinique / urgences'", "metrics": q3}
    ]

    max_search_time_ms = max(b["metrics"]["elapsed_ms"] for b in benchmarks)
    all_under_15ms = all(b["metrics"]["elapsed_ms"] < 15.0 for b in benchmarks)

    return {
        "status": "success",
        "cache_path": cache_path,
        "total_facilities_in_ram": len(searcher.facilities),
        "load_time_ms": load_time_ms,
        "benchmarks": benchmarks,
        "max_search_time_ms": max_search_time_ms,
        "meets_target_15ms": all_under_15ms
    }


def main():
    parser = argparse.ArgumentParser(description="Consommateur de cache mobile hors-ligne Santé DZ Medizy")
    parser.add_argument("--cache-path", default=DEFAULT_CACHE_PATH, help="Chemin du cache GZIP")
    parser.add_argument("--benchmark", action="store_true", default=True, help="Exécuter les 3 requêtes types de référence")
    args = parser.parse_args()

    try:
        report = run_benchmark(cache_path=args.cache_path)
        print("=" * 70)
        print("SANTÉ DZ MEDIZY — CLIENT DE RÉFÉRENCE CACHE MOBILE (OFFLINE)")
        print("=" * 70)
        print(f"Archive chargée    : {report['cache_path']}")
        print(f"Fiches en mémoire  : {report['total_facilities_in_ram']:,}")
        print(f"Temps de chargement: {report['load_time_ms']} ms")
        print("-" * 70)
        print("RÉSULTATS DES REQUÊTES TYPES :")
        for b in report["benchmarks"]:
            m = b["metrics"]
            status_flag = "OK < 15ms" if m["elapsed_ms"] < 15.0 else "! >= 15ms"
            print(f"  • {b['name']:<35} : {m['total_matches']:>3} fiches trouvées en {m['elapsed_ms']:>6.3f} ms [{status_flag}]")
        print("-" * 70)
        print(f"Temps max observé  : {report['max_search_time_ms']} ms")
        print(f"Objectif de perf   : {'VALIDÉ (< 15 ms)' if report['meets_target_15ms'] else 'ATTENTION (> 15 ms)'}")
        print("=" * 70)
        sys.exit(0)
    except Exception as e:
        print(f"[ERREUR] Échec du consommateur mobile : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
