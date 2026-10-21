# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Data Quality Checker
=========================================
Calcule des métriques de qualité sur un DataFrame pandas ou une liste de dicts.

Métriques :
- total
- gps coverage
- phone coverage
- address coverage
- website coverage
- category coverage
- place_id coverage
- rating coverage
- opening_hours coverage
- duplicate rate
- wilaya coverage
"""

from typing import Any, Dict, List


class DataQualityChecker:
    def __init__(self, rows: List[dict]):
        self.rows = rows or []

    def _count_filled(self, field: str) -> int:
        return sum(1 for r in self.rows if str(r.get(field, "")).strip())

    def _count_gps(self) -> int:
        return sum(
            1 for r in self.rows
            if str(r.get("latitude", "")).strip() and str(r.get("longitude", "")).strip()
        )

    def _count_non_empty(self, values: List[str]) -> int:
        return sum(1 for v in values if str(v).strip())

    def compute(self) -> Dict[str, Any]:
        total = len(self.rows)
        if total == 0:
            return {"total": 0}

        metrics = {
            "total": total,
            "gps": self._count_gps(),
            "phone": self._count_filled("telephone"),
            "address": self._count_filled("adresse"),
            "website": self._count_filled("site_web"),
            "category": self._count_filled("categorie_recherche"),
            "place_id": self._count_filled("place_id_si_visible"),
            "rating": self._count_filled("note"),
            "review_count": self._count_filled("nombre_avis"),
            "opening_hours": self._count_filled("horaires"),
            "wilaya": self._count_filled("wilaya"),
            "commune": self._count_filled("commune"),
        }

        # Pourcentage
        pct = {}
        for key, count in metrics.items():
            if key == "total":
                continue
            pct[key + "_pct"] = round(100.0 * count / total, 2)

        # Taux de doublons estimé par stable_key legacy
        seen = set()
        duplicates = 0
        for r in self.rows:
            raw = "|".join([
                str(r.get("nom", "") or "").lower().strip(),
                str(r.get("adresse", "") or "").lower().strip(),
                str(r.get("telephone", "") or "").strip(),
                str(r.get("latitude") or ""),
                str(r.get("longitude") or ""),
            ])
            key = raw
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
        metrics["duplicates_estimate"] = duplicates
        pct["duplicates_estimate_pct"] = round(100.0 * duplicates / total, 2) if total else 0.0

        # Couverture wilayas
        wilayas = sorted({str(r.get("wilaya", "")).strip() for r in self.rows if str(r.get("wilaya", "")).strip()})
        metrics["unique_wilayas"] = len(wilayas)
        metrics["wilayas_list"] = wilayas

        result = {"metrics": metrics, "coverage": pct}
        return result

    def to_text_report(self) -> str:
        data = self.compute()
        lines = []
        lines.append("=" * 60)
        lines.append("MEDIZY — DATA QUALITY REPORT")
        lines.append("=" * 60)
        m = data["metrics"]
        c = data["coverage"]
        lines.append(f"TOTAL                 : {m['total']}")
        lines.append(f"WILAYAS               : {m['unique_wilayas']}")
        lines.append(f"GPS                   : {m['gps']} / {m['total']} ({c.get('gps_pct', 0)} %)")
        lines.append(f"TÉLÉPHONES            : {m['phone']} / {m['total']} ({c.get('phone_pct', 0)} %)")
        lines.append(f"ADRESSES              : {m['address']} / {m['total']} ({c.get('address_pct', 0)} %)")
        lines.append(f"SITES WEB             : {m['website']} / {m['total']} ({c.get('website_pct', 0)} %)")
        lines.append(f"CATÉGORIES            : {m['category']} / {m['total']} ({c.get('category_pct', 0)} %)")
        lines.append(f"PLACE ID              : {m['place_id']} / {m['total']} ({c.get('place_id_pct', 0)} %)")
        lines.append(f"NOTES                 : {m['rating']} / {m['total']} ({c.get('rating_pct', 0)} %)")
        lines.append(f"HORAIRES              : {m['opening_hours']} / {m['total']} ({c.get('opening_hours_pct', 0)} %)")
        lines.append(f"COMMUNES              : {m['commune']} / {m['total']} ({c.get('commune_pct', 0)} %)")
        lines.append(f"DOUBLONS ESTIMÉS      : {m['duplicates_estimate']} ({c.get('duplicates_estimate_pct', 0)} %)")
        lines.append("=" * 60)
        return "\n".join(lines)
