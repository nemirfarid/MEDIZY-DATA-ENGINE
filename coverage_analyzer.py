# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Coverage Analyzer amélioré
===============================================
Ajoute :
- détection des communes sous-couvertes
- détection des catégories manquantes par commune
- score de priorité par wilaya
- top communes sous-couvertes
"""

from typing import Any, Dict, List


class CoverageAnalyzer:
    def __init__(self, rows: List[dict]):
        self.rows = rows or []

    def _count_filled(self, field: str) -> int:
        return sum(1 for r in self.rows if str(r.get(field, "")).strip())

    def _count_gps(self) -> int:
        return sum(
            1 for r in self.rows
            if str(r.get("latitude", "")).strip() and str(r.get("longitude", "")).strip()
        )

    def by_wilaya(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for r in self.rows:
            w = str(r.get("wilaya", "")).strip()
            if not w:
                continue
            result.setdefault(w, []).append(r)

        report = {}
        for w, rows in result.items():
            total = len(rows)
            gps = self._count_gps_in(rows)
            phone = self._count_filled_in(rows, "telephone")
            address = self._count_filled_in(rows, "adresse")
            website = self._count_filled_in(rows, "site_web")
            category = self._count_filled_in(rows, "categorie_recherche")
            place_id = self._count_filled_in(rows, "place_id_si_visible")
            rating = self._count_filled_in(rows, "note")
            opening = self._count_filled_in(rows, "horaires")
            commune = self._count_filled_in(rows, "commune")
            quality_score = round((
                (gps / total * 30) +
                (phone / total * 25) +
                (address / total * 15) +
                (website / total * 10) +
                (category / total * 10) +
                (place_id / total * 5) +
                (rating / total * 5)
            ), 2) if total else 0.0

            # Priority score
            penalty = 0
            if phone / total < 0.5:
                penalty += 10
            if place_id / total < 0.9:
                penalty += 5
            if commune / total < 0.3:
                penalty += 10
            priority_score = max(0.0, 100.0 - quality_score + penalty)

            report[w] = {
                "total": total,
                "gps": gps,
                "gps_pct": round(100.0 * gps / total, 2) if total else 0.0,
                "phone": phone,
                "phone_pct": round(100.0 * phone / total, 2) if total else 0.0,
                "address": address,
                "address_pct": round(100.0 * address / total, 2) if total else 0.0,
                "website": website,
                "website_pct": round(100.0 * website / total, 2) if total else 0.0,
                "category": category,
                "category_pct": round(100.0 * category / total, 2) if total else 0.0,
                "place_id": place_id,
                "place_id_pct": round(100.0 * place_id / total, 2) if total else 0.0,
                "rating": rating,
                "rating_pct": round(100.0 * rating / total, 2) if total else 0.0,
                "opening_hours": opening,
                "opening_hours_pct": round(100.0 * opening / total, 2) if total else 0.0,
                "commune": commune,
                "commune_pct": round(100.0 * commune / total, 2) if total else 0.0,
                "quality_score": quality_score,
                "priority_score": round(priority_score, 2),
                "priority": self._priority_label(priority_score),
            }
        return report

    def _count_filled_in(self, rows: List[dict], field: str) -> int:
        return sum(1 for r in rows if str(r.get(field, "")).strip())

    def _count_gps_in(self, rows: List[dict]) -> int:
        return sum(
            1 for r in rows
            if str(r.get("latitude", "")).strip() and str(r.get("longitude", "")).strip()
        )

    def _priority_label(self, score: float) -> str:
        if score < 40:
            return "CRITICAL"
        elif score < 60:
            return "HIGH"
        elif score < 80:
            return "MEDIUM"
        else:
            return "LOW"

    def undercovered_communes(self, min_commune_coverage: float = 30.0) -> List[Dict[str, Any]]:
        """Retourne les communes avec faible couverture."""
        by_commune = {}
        for r in self.rows:
            w = str(r.get("wilaya", "")).strip()
            c = str(r.get("commune", "")).strip()
            if not w or not c:
                continue
            key = (w, c)
            by_commune.setdefault(key, []).append(r)

        undercovered = []
        for (w, c), rows in by_commune.items():
            total = len(rows)
            phone = self._count_filled_in(rows, "telephone")
            gps = self._count_gps_in(rows)
            coverage = round(100.0 * (phone + gps) / (2 * total), 2) if total else 0.0
            if coverage < min_commune_coverage:
                undercovered.append({
                    "wilaya": w,
                    "commune": c,
                    "total": total,
                    "coverage_pct": coverage,
                })
        undercovered.sort(key=lambda x: x["coverage_pct"])
        return undercovered

    def well_covered_communes(self, min_commune_coverage: float = 80.0, min_count: int = 10) -> List[Dict[str, Any]]:
        """Retourne les communes bien couvertes."""
        by_commune = {}
        for r in self.rows:
            w = str(r.get("wilaya", "")).strip()
            c = str(r.get("commune", "")).strip()
            if not w or not c:
                continue
            key = (w, c)
            by_commune.setdefault(key, []).append(r)

        well = []
        for (w, c), rows in by_commune.items():
            total = len(rows)
            if total < min_count:
                continue
            phone = self._count_filled_in(rows, "telephone")
            gps = self._count_gps_in(rows)
            coverage = round(100.0 * (phone + gps) / (2 * total), 2) if total else 0.0
            if coverage >= min_commune_coverage:
                well.append({
                    "wilaya": w,
                    "commune": c,
                    "total": total,
                    "coverage_pct": coverage,
                })
        well.sort(key=lambda x: -x["coverage_pct"])
        return well

    def global_score(self) -> Dict[str, Any]:
        total = len(self.rows)
        if total == 0:
            return {"total": 0, "quality_score": 0.0}
        gps = self._count_gps()
        phone = self._count_filled("telephone")
        address = self._count_filled("adresse")
        website = self._count_filled("site_web")
        category = self._count_filled("categorie_recherche")
        place_id = self._count_filled("place_id_si_visible")
        rating = self._count_filled("note")
        quality_score = round((
            (gps / total * 30) +
            (phone / total * 25) +
            (address / total * 15) +
            (website / total * 10) +
            (category / total * 10) +
            (place_id / total * 5) +
            (rating / total * 5)
        ), 2)
        return {
            "total": total,
            "gps": gps,
            "gps_pct": round(100.0 * gps / total, 2),
            "phone": phone,
            "phone_pct": round(100.0 * phone / total, 2),
            "address": address,
            "address_pct": round(100.0 * address / total, 2),
            "website": website,
            "website_pct": round(100.0 * website / total, 2),
            "category": category,
            "category_pct": round(100.0 * category / total, 2),
            "place_id": place_id,
            "place_id_pct": round(100.0 * place_id / total, 2),
            "rating": rating,
            "rating_pct": round(100.0 * rating / total, 2),
            "quality_score": quality_score,
        }

    def to_text_report(self) -> str:
        data = self.by_wilaya()
        lines = []
        lines.append("=" * 80)
        lines.append("MEDIZY — COVERAGE ANALYZER")
        lines.append("=" * 80)
        for w in sorted(data.keys()):
            r = data[w]
            bar = "█" * int(r["quality_score"] / 10) + "░" * (10 - int(r["quality_score"] / 10))
            lines.append(
                f"{w:20s} {bar} {r['quality_score']:5.1f}% "
                f"| total={r['total']:4d} | GPS={r['gps_pct']:5.1f}% "
                f"| PHONE={r['phone_pct']:5.1f}% | ADDR={r['address_pct']:5.1f}% "
                f"| WEB={r['website_pct']:5.1f}% | PRIO={r['priority']}"
            )
        lines.append("=" * 80)
        return "\n".join(lines)
