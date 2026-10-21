# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Yield Analyzer
====================================
Mesure le rendement des requêtes de scraping.

Métriques par requête :
- results_found : résultats trouvés sur la page
- new_unique : nouvelles fiches uniques ajoutées
- duplicates : doublons détectés
- new_gps : nouvelles fiches avec GPS
- new_phones : nouvelles fiches avec téléphone
- yield_pct : pourcentage de rendement = new_unique / results_found

Règles d'arrêt :
- MIN_NEW_PER_QUERY : minimum de nouvelles fiches par requête
- MAX_EMPTY_STREAK : nombre de requêtes vides consécutives avant arrêt
- MIN_YIELD_PCT : pourcentage minimum de rendement
"""

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class QueryYield:
    wilaya: str
    commune: str
    category: str
    query: str
    results_found: int = 0
    new_unique: int = 0
    duplicates: int = 0
    new_gps: int = 0
    new_phones: int = 0
    yield_pct: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class YieldAnalyzer:
    def __init__(self, min_new_per_query: int = 3, max_empty_streak: int = 3, min_yield_pct: float = 5.0):
        self.yields: List[QueryYield] = []
        self.min_new_per_query = min_new_per_query
        self.max_empty_streak = max_empty_streak
        self.min_yield_pct = min_yield_pct

    def record(self, yield_data: QueryYield):
        self.yields.append(yield_data)

    def should_stop_category(self, wilaya: str, commune: str, category: str) -> bool:
        """Détermine si une catégorie/commune doit être arrêtée."""
        recent = [
            y for y in self.yields[-10:]
            if y.wilaya == wilaya and y.commune == commune and y.category == category
        ]
        if len(recent) < self.max_empty_streak:
            return False
        empty_count = sum(1 for y in recent if y.new_unique == 0)
        return empty_count >= self.max_empty_streak

    def get_low_yield_queries(self) -> List[QueryYield]:
        """Retourne les requêtes avec rendement insuffisant."""
        return [y for y in self.yields if y.yield_pct < self.min_yield_pct]

    def get_empty_streaks(self) -> List[List[QueryYield]]:
        """Détecte les séries de requêtes vides par wilaya/commune/catégorie."""
        streaks = []
        current_streak = []
        for y in self.yields:
            if y.new_unique == 0 and y.results_found == 0:
                current_streak.append(y)
            else:
                if len(current_streak) >= self.max_empty_streak:
                    streaks.append(current_streak)
                current_streak = []
        if len(current_streak) >= self.max_empty_streak:
            streaks.append(current_streak)
        return streaks

    def top_categories_by_yield(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Retourne les catégories avec le meilleur rendement."""
        cat_stats: Dict[str, Dict[str, int]] = {}
        for y in self.yields:
            key = y.category
            if key not in cat_stats:
                cat_stats[key] = {"results": 0, "new": 0, "count": 0}
            cat_stats[key]["results"] += y.results_found
            cat_stats[key]["new"] += y.new_unique
            cat_stats[key]["count"] += 1
        ranked = []
        for cat, stats in cat_stats.items():
            yield_pct = round(100.0 * stats["new"] / stats["results"], 2) if stats["results"] else 0.0
            ranked.append({
                "category": cat,
                "total_results": stats["results"],
                "total_new": stats["new"],
                "queries": stats["count"],
                "yield_pct": yield_pct,
            })
        ranked.sort(key=lambda x: -x["yield_pct"])
        return ranked[:top_n]

    def top_wilayas_by_yield(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Retourne les wilayas avec le meilleur rendement."""
        w_stats: Dict[str, Dict[str, int]] = {}
        for y in self.yields:
            key = y.wilaya
            if key not in w_stats:
                w_stats[key] = {"results": 0, "new": 0, "count": 0}
            w_stats[key]["results"] += y.results_found
            w_stats[key]["new"] += y.new_unique
            w_stats[key]["count"] += 1
        ranked = []
        for w, stats in w_stats.items():
            yield_pct = round(100.0 * stats["new"] / stats["results"], 2) if stats["results"] else 0.0
            ranked.append({
                "wilaya": w,
                "total_results": stats["results"],
                "total_new": stats["new"],
                "queries": stats["count"],
                "yield_pct": yield_pct,
            })
        ranked.sort(key=lambda x: -x["yield_pct"])
        return ranked[:top_n]

    def to_report(self) -> Dict[str, Any]:
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_yields": len(self.yields),
            "avg_yield_pct": round(
                sum(y.yield_pct for y in self.yields) / len(self.yields), 2
            ) if self.yields else 0.0,
            "low_yield_count": len(self.get_low_yield_queries()),
            "empty_streaks_count": len(self.get_empty_streaks()),
            "top_categories": self.top_categories_by_yield(),
            "top_wilayas": self.top_wilayas_by_yield(),
            "config": {
                "min_new_per_query": self.min_new_per_query,
                "max_empty_streak": self.max_empty_streak,
                "min_yield_pct": self.min_yield_pct,
            },
        }
