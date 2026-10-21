# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Smart Coverage Engine
==========================================
Détermine automatiquement où le scraping complémentaire est le plus utile.

Méthode :
1. Analyser la couverture existante par wilaya/commune/catégorie
2. Détecter les trous (under-covered)
3. Calculer un priority_score
4. Proposer des requêtes ciblées
5. Mesurer le rendement après chaque requête
6. S'arrêter quand le rendement devient trop faible

Règles d'arrêt configurables :
- MIN_NEW_PER_QUERY : minimum de nouvelles fiches par requête
- MAX_EMPTY_STREAK : nombre de requêtes vides consécutives avant arrêt
- MIN_YIELD_PCT : pourcentage minimum de rendement
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from coverage_analyzer import CoverageAnalyzer
from communes_officielles import get_communes_by_wilaya, get_all_communes, detect_commune_from_address


@dataclass
class CoverageGap:
    wilaya: str
    commune: str
    category: str
    current_count: int
    gap_score: float = 0.0
    priority: str = "LOW"  # CRITICAL, HIGH, MEDIUM, LOW
    reason: str = ""


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


class SmartCoverageEngine:
    def __init__(
        self,
        rows: List[dict],
        min_new_per_query: int = 3,
        max_empty_streak: int = 3,
        min_yield_pct: float = 5.0,
    ):
        self.rows = rows or []
        self.analyzer = CoverageAnalyzer(rows)
        self.min_new_per_query = min_new_per_query
        self.max_empty_streak = max_empty_streak
        self.min_yield_pct = min_yield_pct
        self.yields: List[QueryYield] = []
        self.gaps: List[CoverageGap] = []

    def analyze_gaps(self) -> List[CoverageGap]:
        """Identifie les communes/catégories sous-couvertes."""
        by_wilaya = {}
        for r in self.rows:
            w = str(r.get("wilaya", "")).strip()
            c = str(r.get("commune", "")).strip()
            cat = str(r.get("categorie_recherche", "")).strip()
            by_wilaya.setdefault(w, {}).setdefault(c, set()).add(cat)

        gaps = []
        for w, communes in by_wilaya.items():
            for commune, cats in communes.items():
                # Catégories manquantes pour cette commune
                all_cats = set([
                    "médecin", "cabinet médical", "médecin généraliste", "médecin spécialiste",
                    "dentiste", "cabinet dentaire", "pharmacie", "laboratoire médical",
                    "clinique", "hôpital", "polyclinique", "centre médical", "centre de santé",
                    "radiologue", "centre de radiologie", "kinésithérapeute", "kinésithérapie",
                    "sage-femme", "ophtalmologue", "pédiatre", "gynécologue", "cardiologue",
                    "dermatologue", "ORL", "neurologue", "urologue", "gastro-entérologue",
                    "psychologue", "psychiatre", "nutritionniste", "orthophoniste", "ostéopathe",
                    "vétérinaire", "centre d'imagerie médicale",
                ])
                missing = all_cats - cats
                for cat in missing:
                    gaps.append(CoverageGap(
                        wilaya=w,
                        commune=commune,
                        category=cat,
                        current_count=0,
                        gap_score=100.0,
                        priority="CRITICAL",
                        reason="Catégorie absente",
                    ))

        # Trier par priorité décroissante
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        gaps.sort(key=lambda g: (priority_order.get(g.priority, 9), -g.gap_score))
        self.gaps = gaps
        return gaps

    def calculate_wilaya_scores(self) -> List[Dict[str, Any]]:
        """Calcule le coverage_score et priority_score par wilaya."""
        report = self.analyzer.by_wilaya()
        scores = []
        for w, data in report.items():
            # coverage_score = qualité globale
            coverage_score = data.get("quality_score", 0.0)
            # priority_score = inverse de la couverture + pénalités
            penalty = 0
            if data.get("phone_pct", 0) < 50:
                penalty += 10
            if data.get("place_id_pct", 0) < 90:
                penalty += 5
            if data.get("commune_pct", 0) < 30:
                penalty += 10
            priority_score = max(0.0, 100.0 - coverage_score + penalty)

            # Niveau de priorité
            if priority_score < 40:
                priority = "CRITICAL"
            elif priority_score < 60:
                priority = "HIGH"
            elif priority_score < 80:
                priority = "MEDIUM"
            else:
                priority = "LOW"

            scores.append({
                "wilaya": w,
                "coverage_score": coverage_score,
                "priority_score": round(priority_score, 2),
                "priority": priority,
                "total": data.get("total", 0),
                "gps_pct": data.get("gps_pct", 0),
                "phone_pct": data.get("phone_pct", 0),
                "address_pct": data.get("address_pct", 0),
                "website_pct": data.get("website_pct", 0),
                "place_id_pct": data.get("place_id_pct", 0),
                "commune_pct": data.get("commune_pct", 0),
            })
        scores.sort(key=lambda x: -x["priority_score"])
        return scores

    def record_yield(self, yield_data: QueryYield):
        self.yields.append(yield_data)

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

    def should_stop_category(self, wilaya: str, commune: str, category: str) -> bool:
        """Détermine si une catégorie/commune doit être arrêtée."""
        recent = [y for y in self.yields[-5:] if y.wilaya == wilaya and y.commune == commune and y.category == category]
        if len(recent) < 3:
            return False
        empty_count = sum(1 for y in recent if y.new_unique == 0)
        return empty_count >= self.max_empty_streak

    def to_report(self) -> Dict[str, Any]:
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_rows": len(self.rows),
            "wilaya_scores": self.calculate_wilaya_scores(),
            "gaps_count": len(self.gaps),
            "top_gaps": [asdict(g) for g in self.gaps[:20]],
            "yields_count": len(self.yields),
            "low_yield_count": len(self.get_low_yield_queries()),
            "empty_streaks_count": len(self.get_empty_streaks()),
            "avg_yield_pct": round(sum(y.yield_pct for y in self.yields) / len(self.yields), 2) if self.yields else 0.0,
        }
