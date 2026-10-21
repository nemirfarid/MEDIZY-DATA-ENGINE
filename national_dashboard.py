# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — National Dashboard
=======================================
Tableau de bord national en temps réel.
Affiche dans le terminal les métriques clés.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from coverage_analyzer import CoverageAnalyzer
from smart_coverage_engine import SmartCoverageEngine


class NationalDashboard:
    def __init__(self, rows: List[dict]):
        self.rows = rows or []
        self.analyzer = CoverageAnalyzer(rows)
        self.engine = SmartCoverageEngine(rows)

    def render(self) -> str:
        global_score = self.analyzer.global_score()
        wilaya_scores = self.analyzer.by_wilaya()
        undercovered = self.analyzer.undercovered_communes()
        well_covered = self.analyzer.well_covered_communes()
        gaps = self.engine.analyze_gaps()

        lines = []
        lines.append("=" * 80)
        lines.append("MEDIZY NATIONAL SCRAPER — TABLEAU DE BORD")
        lines.append("=" * 80)
        lines.append(f"Généré le : {datetime.now().isoformat(timespec='seconds')}")
        lines.append("")
        lines.append(f"TOTAL UNIQUE        : {global_score['total']}")
        lines.append(f"GPS                 : {global_score['gps']} / {global_score['total']} ({global_score['gps_pct']} %)")
        lines.append(f"TÉLÉPHONES          : {global_score['phone']} / {global_score['total']} ({global_score['phone_pct']} %)")
        lines.append(f"ADRESSES            : {global_score['address']} / {global_score['total']} ({global_score['address_pct']} %)")
        lines.append(f"SITES WEB           : {global_score['website']} / {global_score['total']} ({global_score['website_pct']} %)")
        lines.append(f"CATÉGORIES          : {global_score['category']} / {global_score['total']} ({global_score['category_pct']} %)")
        lines.append(f"PLACE ID            : {global_score['place_id']} / {global_score['total']} ({global_score['place_id_pct']} %)")
        lines.append(f"NOTES               : {global_score['rating']} / {global_score['total']} ({global_score['rating_pct']} %)")
        lines.append(f"COMMUNES            : {global_score.get('commune', 0)} / {global_score['total']} ({global_score.get('commune_pct', 0)} %)")
        lines.append(f"QUALITÉ GLOBALE     : {global_score['quality_score']}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("WILAYAS")
        lines.append("-" * 80)
        for w in sorted(wilaya_scores.keys()):
            r = wilaya_scores[w]
            bar = "█" * int(r["quality_score"] / 10) + "░" * (10 - int(r["quality_score"] / 10))
            lines.append(
                f"{w:20s} {bar} {r['quality_score']:5.1f}% "
                f"| total={r['total']:4d} | GPS={r['gps_pct']:5.1f}% "
                f"| PHONE={r['phone_pct']:5.1f}% | PRIO={r['priority']}"
            )
        lines.append("")
        lines.append("-" * 80)
        lines.append("COMMUNES SOUS-COUVERTES (TOP 20)")
        lines.append("-" * 80)
        for uc in undercovered[:20]:
            lines.append(
                f"{uc['wilaya']:20s} {uc['commune']:25s} "
                f"| total={uc['total']:4d} | coverage={uc['coverage_pct']:5.1f}%"
            )
        lines.append("")
        lines.append("-" * 80)
        lines.append("COMMUNES BIEN COUVERTES (TOP 10)")
        lines.append("-" * 80)
        for wc in well_covered[:10]:
            lines.append(
                f"{wc['wilaya']:20s} {wc['commune']:25s} "
                f"| total={wc['total']:4d} | coverage={wc['coverage_pct']:5.1f}%"
            )
        lines.append("")
        lines.append("-" * 80)
        lines.append("TROUS DE COUVERTURE (catégories manquantes)")
        lines.append("-" * 80)
        for g in gaps[:20]:
            lines.append(
                f"{g.wilaya:20s} {g.commune:25s} {g.category:25s} | {g.priority} | {g.reason}"
            )
        lines.append("=" * 80)
        return "\n".join(lines)

    def to_html(self, output_path: Path):
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>MEDIZY Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #4CAF50; color: white; }}
.bar {{ background-color: #4CAF50; height: 20px; }}
</style>
</head>
<body>
<h1>MEDIZY National Dashboard</h1>
<p>Généré le {datetime.now().isoformat(timespec='seconds')}</p>
<h2>Résumé</h2>
<ul>
<li>TOTAL: {self.analyzer.global_score()['total']}</li>
<li>GPS: {self.analyzer.global_score()['gps_pct']}%</li>
<li>TÉLÉPHONES: {self.analyzer.global_score()['phone_pct']}%</li>
<li>PLACE ID: {self.analyzer.global_score()['place_id_pct']}%</li>
</ul>
</body>
</html>"""
        output_path.write_text(html, encoding="utf-8")
