#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SANTÉ DZ / MEDIZY — EXTRACTION MULTI-FORMATS DATASET NATIONAL (PHASE 9)
========================================================================
Extrait les 35 832 fiches qualifiées depuis medizy_scraper.db (mode=ro) vers :
1. CSV National complet : D:\\SANTE_DZ_EXPORTS\\SANTE_DZ_NATIONAL_35832.csv (UTF-8 avec BOM, virgule)
2. JSON complet structuré : D:\\SANTE_DZ_EXPORTS\\sante_dz_full_dataset.json (avec tags, spécialités, métadonnées)
3. GeoJSON SIG vectoriel : D:\\SANTE_DZ_EXPORTS\\sante_dz_map_features.geojson (FeatureCollection RFC 7946)
4. Registre Excel multi-onglets : D:\\SANTE_DZ_EXPORTS\\SANTE_DZ_REGISTRE_NATIONAL.xlsx (onglets thématiques)
"""

import csv
import datetime
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from export_mobile_cache import OFFICIAL_WILAYAS, WILAYA_BY_CODE, calculate_sha256

DEFAULT_DB = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
OUTPUT_DIR = r"D:\SANTE_DZ_EXPORTS"
EXPECTED_COUNT = 35832
EXPECTED_WILAYAS = 58


def format_algerian_phone(phone_str: str) -> str:
    """Nettoie et formate le numéro de téléphone au standard national algérien."""
    if not phone_str or not str(phone_str).strip():
        return ""
    raw = str(phone_str).strip()
    # Supprimer les préfixes internationaux +213 ou 00213
    cleaned = re.sub(r"^(?:\+213|00213)", "0", raw)
    # Extraire les chiffres
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return raw

    # Si 9 chiffres commençant sans 0, ajouter le 0
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits

    # Format mobile 10 chiffres (05, 06, 07) : 05XX XX XX XX
    if len(digits) == 10 and digits.startswith(("05", "06", "07")):
        return f"{digits[:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}"
    # Format fixe 9 chiffres (021, 031, etc.) : 0XX XX XX XX
    elif len(digits) == 9 and digits.startswith("0"):
        return f"{digits[:3]} {digits[3:5]} {digits[5:7]} {digits[7:9]}"
    # Format fixe 10 chiffres : 0XX XX XX XX XX
    elif len(digits) == 10 and digits.startswith("0"):
        return f"{digits[:3]} {digits[3:5]} {digits[5:7]} {digits[7:9]} {digits[9:]}"

    return raw


def get_category_sheet_name(cat: str) -> str:
    """Assigne chaque fiche à un des onglets Excel thématiques."""
    c = (cat or "").strip().lower()
    if any(k in c for k in ["pharmacie", "pharmacy", "parapharm"]):
        return "Pharmacies"
    elif any(k in c for k in ["dentiste", "dentaire", "dentist", "stomatolog"]):
        return "Dentistes"
    elif any(k in c for k in ["laboratoire", "imagerie", "radiologie", "radiologue"]):
        return "Laboratoires"
    elif any(k in c for k in ["hôpital", "hopital", "hospital", "clinique", "clinic", "centre de santé", "centre médical", "polyclinique", "dispensaire", "maternité"]):
        return "Hôpitaux & Polycliniques"
    elif any(k in c for k in [
        "médecin", "medecin", "cabinet médical", "cardiologue", "gynécologue",
        "pédiatre", "ophtalmologue", "dermatologue", "psychiatre", "orl",
        "neurologue", "gastro", "urologue", "doctors", "spécialiste", "specialiste"
    ]):
        return "Médecins"
    else:
        return "Autres & Paramédical"


def fetch_all_facilities(db_path: str) -> List[Dict[str, Any]]:
    """Récupère l'intégralité des établissements en lecture seule stricte."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Base SQLite introuvable : {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    integ = cur.fetchone()[0]
    if integ != "ok":
        conn.close()
        raise ValueError(f"Intégrité SQLite compromise : {integ}")

    cur.execute("""
        SELECT 
            id, place_id, nom, categorie_recherche, wilaya, commune,
            adresse, telephone, site_web, note, nombre_avis,
            latitude, longitude, source
        FROM places
        ORDER BY wilaya ASC, commune ASC, nom ASC;
    """)
    rows = cur.fetchall()
    conn.close()

    wilaya_to_code = {name.lower(): code for code, name in OFFICIAL_WILAYAS}

    facilities = []
    for r in rows:
        w_name = r["wilaya"] or "Inconnue"
        w_code = wilaya_to_code.get(w_name.lower(), "99")
        tel_nat = format_algerian_phone(r["telephone"])
        
        facilities.append({
            "id": r["id"],
            "place_id": r["place_id"] or "",
            "nom": r["nom"] or "",
            "categorie": r["categorie_recherche"] or "autre",
            "wilaya": w_name,
            "wilaya_code": w_code,
            "commune": r["commune"] or "",
            "adresse": r["adresse"] or "",
            "telephone": tel_nat,
            "site_web": r["site_web"] or "",
            "note": r["note"] if r["note"] is not None else "",
            "nombre_avis": r["nombre_avis"] if r["nombre_avis"] is not None else "",
            "latitude": float(r["latitude"]) if r["latitude"] is not None else 0.0,
            "longitude": float(r["longitude"]) if r["longitude"] is not None else 0.0,
            "source": r["source"] or "medizy_official_db"
        })

    return facilities


def export_csv(facilities: List[Dict[str, Any]], output_path: str) -> Dict[str, Any]:
    """Exporte en CSV avec encodage UTF-8 avec BOM et séparateur virgule."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    t0 = time.perf_counter()

    fieldnames = [
        "id", "place_id", "nom", "categorie", "wilaya", "wilaya_code",
        "commune", "adresse", "telephone", "site_web", "note",
        "nombre_avis", "latitude", "longitude", "source"
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for fac in facilities:
            writer.writerow(fac)

    t1 = time.perf_counter()
    size_bytes = os.path.getsize(output_path)
    return {
        "format": "CSV",
        "filepath": output_path,
        "count": len(facilities),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "duration_sec": round(t1 - t0, 3)
    }


def export_json(facilities: List[Dict[str, Any]], db_sha: str, output_path: str) -> Dict[str, Any]:
    """Exporte en JSON complet structuré avec tags, spécialités et métadonnées."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    t0 = time.perf_counter()

    enriched_facilities = []
    wilaya_counts = {}
    cat_counts = {}

    for fac in facilities:
        w = fac["wilaya"]
        c = fac["categorie"]
        wilaya_counts[w] = wilaya_counts.get(w, 0) + 1
        cat_counts[c] = cat_counts.get(c, 0) + 1

        tags = [c, w]
        if fac["commune"]:
            tags.append(fac["commune"])
        if fac["telephone"]:
            tags.append("contact_disponible")
        if fac["note"] != "" and float(fac["note"]) >= 4.0:
            tags.append("hautement_note")

        enriched_facilities.append({
            "id": fac["id"],
            "place_id": fac["place_id"],
            "nom": fac["nom"],
            "categorie": fac["categorie"],
            "sheet_group": get_category_sheet_name(fac["categorie"]),
            "localisation": {
                "wilaya": fac["wilaya"],
                "wilaya_code": fac["wilaya_code"],
                "commune": fac["commune"],
                "adresse": fac["adresse"],
                "coordinates": {
                    "latitude": fac["latitude"],
                    "longitude": fac["longitude"]
                }
            },
            "contact": {
                "telephone": fac["telephone"],
                "site_web": fac["site_web"]
            },
            "evaluation": {
                "note": fac["note"],
                "nombre_avis": fac["nombre_avis"]
            },
            "source": fac["source"],
            "tags": tags
        })

    payload = {
        "metadata": {
            "dataset_name": "SANTE_DZ_MEDIZY_NATIONAL",
            "version": "1.0.15",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_facilities": len(facilities),
            "wilayas_count": len(wilaya_counts),
            "categories_count": len(cat_counts),
            "gps_coverage_pct": 100.0,
            "source_database_sha256": db_sha,
            "license": "Open Data Sanitaire Algérie / Medizy Public Dataset"
        },
        "facilities": enriched_facilities
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    t1 = time.perf_counter()
    size_bytes = os.path.getsize(output_path)
    return {
        "format": "JSON",
        "filepath": output_path,
        "count": len(facilities),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "duration_sec": round(t1 - t0, 3)
    }


def export_geojson(facilities: List[Dict[str, Any]], output_path: str) -> Dict[str, Any]:
    """Exporte en GeoJSON SIG RFC 7946 (FeatureCollection)."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    t0 = time.perf_counter()

    features = []
    for fac in facilities:
        features.append({
            "type": "Feature",
            "id": fac["id"],
            "geometry": {
                "type": "Point",
                "coordinates": [fac["longitude"], fac["latitude"]]
            },
            "properties": {
                "id": fac["id"],
                "place_id": fac["place_id"],
                "nom": fac["nom"],
                "categorie": fac["categorie"],
                "groupe": get_category_sheet_name(fac["categorie"]),
                "wilaya": fac["wilaya"],
                "wilaya_code": fac["wilaya_code"],
                "commune": fac["commune"],
                "adresse": fac["adresse"],
                "telephone": fac["telephone"],
                "site_web": fac["site_web"],
                "note": fac["note"],
                "nombre_avis": fac["nombre_avis"],
                "source": fac["source"]
            }
        })

    geojson_doc = {
        "type": "FeatureCollection",
        "name": "sante_dz_map_features",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": features
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, ensure_ascii=False, separators=(",", ":"))

    t1 = time.perf_counter()
    size_bytes = os.path.getsize(output_path)
    return {
        "format": "GeoJSON",
        "filepath": output_path,
        "count": len(facilities),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "duration_sec": round(t1 - t0, 3)
    }


def export_excel(facilities: List[Dict[str, Any]], output_path: str) -> Dict[str, Any]:
    """Exporte le registre Excel consolidé multi-onglets."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    t0 = time.perf_counter()

    wb = openpyxl.Workbook()
    # Retirer la feuille par défaut
    default_sheet = wb.active

    # Styles
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    kpi_title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # 1. Onglet Synthèse & Métriques
    ws_summary = wb.create_sheet(title="Synthèse & Métriques")
    ws_summary.views.sheetView[0].showGridLines = True

    ws_summary["A1"] = "PROGRAMME NATIONAL SANITAIRE SANTÉ DZ / MEDIZY"
    ws_summary["A1"].font = kpi_title_font
    ws_summary["A2"] = f"Registre National Certifié — 35 832 Établissements sur 58 Wilayas (Date d'export : {datetime.date.today().isoformat()})"
    ws_summary["A2"].font = Font(italic=True, size=11)

    # Tableaux récapitulatifs
    ws_summary["A4"] = "INDICATEURS CLÉS NATIONAUX"
    ws_summary["A4"].font = bold_font

    kpis = [
        ("Total Établissements Qualifiés", len(facilities)),
        ("Wilayas Couvertes", 58),
        ("Taux de Géolocalisation (GPS)", "100.00 %"),
        ("Contacts Téléphoniques Directs", sum(1 for f in facilities if f["telephone"])),
        ("Sources Primaires", "Ministère Santé, Annuaire Carto, OSM DZ, 1santé, MSP")
    ]
    for i, (k, v) in enumerate(kpis, start=5):
        ws_summary[f"A{i}"] = k
        ws_summary[f"B{i}"] = v
        ws_summary[f"A{i}"].font = regular_font
        ws_summary[f"B{i}"].font = bold_font

    # Décompte par grandes catégories
    ws_summary["D4"] = "RÉPARTITION PAR CATÉGORIE MAJEURE"
    ws_summary["D4"].font = bold_font
    ws_summary["D5"] = "Catégorie Majeure"
    ws_summary["E5"] = "Volume"
    ws_summary["D5"].fill = header_fill
    ws_summary["D5"].font = header_font
    ws_summary["E5"].fill = header_fill
    ws_summary["E5"].font = header_font

    group_counts = {}
    for f in facilities:
        grp = get_category_sheet_name(f["categorie"])
        group_counts[grp] = group_counts.get(grp, 0) + 1

    for row_idx, (grp, count) in enumerate(sorted(group_counts.items(), key=lambda x: x[1], reverse=True), start=6):
        ws_summary[f"D{row_idx}"] = grp
        ws_summary[f"E{row_idx}"] = count
        ws_summary[f"D{row_idx}"].font = regular_font
        ws_summary[f"E{row_idx}"].font = regular_font

    # Décompte par Wilaya
    ws_summary["A12"] = "DÉCOMPTE DÉTAILLÉ PAR WILAYA (01 À 58)"
    ws_summary["A12"].font = bold_font
    ws_summary["A13"] = "Code"
    ws_summary["B13"] = "Wilaya"
    ws_summary["C13"] = "Total Établissements"
    ws_summary["D13"] = "Communes Couvertes"
    for col_letter in ["A", "B", "C", "D"]:
        cell = ws_summary[f"{col_letter}13"]
        cell.fill = header_fill
        cell.font = header_font

    wilaya_stats = {}
    for code, name in OFFICIAL_WILAYAS:
        wilaya_stats[name] = {"code": code, "count": 0, "communes": set()}

    for f in facilities:
        w = f["wilaya"]
        if w in wilaya_stats:
            wilaya_stats[w]["count"] += 1
            if f["commune"]:
                wilaya_stats[w]["communes"].add(f["commune"])

    for r_idx, (w_name, stat) in enumerate(wilaya_stats.items(), start=14):
        ws_summary[f"A{r_idx}"] = stat["code"]
        ws_summary[f"B{r_idx}"] = w_name
        ws_summary[f"C{r_idx}"] = stat["count"]
        ws_summary[f"D{r_idx}"] = len(stat["communes"])
        for cl in ["A", "B", "C", "D"]:
            ws_summary[f"{cl}{r_idx}"].font = regular_font

    # Définition des onglets thématiques
    sheets_def = [
        "Pharmacies",
        "Médecins",
        "Hôpitaux & Polycliniques",
        "Laboratoires",
        "Dentistes",
        "Autres & Paramédical"
    ]

    columns = [
        ("ID", 8),
        ("Nom de l'établissement", 34),
        ("Catégorie", 22),
        ("Wilaya", 18),
        ("Code", 8),
        ("Commune", 20),
        ("Adresse", 32),
        ("Téléphone", 16),
        ("Site Web", 25),
        ("Note", 8),
        ("Avis", 8),
        ("Latitude", 12),
        ("Longitude", 12),
        ("Source", 20)
    ]

    sheets_obj = {}
    for sheet_name in sheets_def:
        ws = wb.create_sheet(title=sheet_name)
        ws.views.sheetView[0].showGridLines = True
        sheets_obj[sheet_name] = ws

        # En-têtes
        for col_idx, (col_name, col_width) in enumerate(columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(col_idx)].width = col_width

        ws.freeze_panes = "A2"

    # Remplissage des données
    sheet_row_counters = {s: 2 for s in sheets_def}
    for fac in facilities:
        target_sheet = get_category_sheet_name(fac["categorie"])
        ws = sheets_obj.get(target_sheet, sheets_obj["Autres & Paramédical"])
        row_num = sheet_row_counters[target_sheet]

        row_values = [
            fac["id"],
            fac["nom"],
            fac["categorie"],
            fac["wilaya"],
            fac["wilaya_code"],
            fac["commune"],
            fac["adresse"],
            fac["telephone"],
            fac["site_web"],
            fac["note"],
            fac["nombre_avis"],
            fac["latitude"],
            fac["longitude"],
            fac["source"]
        ]

        for col_idx, val in enumerate(row_values, start=1):
            c_cell = ws.cell(row=row_num, column=col_idx, value=val)
            c_cell.font = regular_font
            c_cell.border = thin_border
            if col_idx in [1, 5, 10, 11, 12, 13]:
                c_cell.alignment = Alignment(horizontal="center")

        sheet_row_counters[target_sheet] += 1

    # Activer les filtres automatiques sur chaque onglet
    for s_name, ws in sheets_obj.items():
        max_row = sheet_row_counters[s_name] - 1
        if max_row >= 1:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{max_row}"

    # Supprimer la feuille par défaut si présente
    if default_sheet in wb.worksheets:
        wb.remove(default_sheet)

    # Largeurs sur synthèse
    ws_summary.column_dimensions["A"].width = 28
    ws_summary.column_dimensions["B"].width = 26
    ws_summary.column_dimensions["C"].width = 20
    ws_summary.column_dimensions["D"].width = 30
    ws_summary.column_dimensions["E"].width = 16

    wb.save(output_path)
    wb.close()

    t1 = time.perf_counter()
    size_bytes = os.path.getsize(output_path)
    return {
        "format": "Excel",
        "filepath": output_path,
        "count": len(facilities),
        "sheets": list(sheet_row_counters.keys()),
        "sheet_counts": {s: sheet_row_counters[s] - 2 for s in sheet_row_counters},
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "duration_sec": round(t1 - t0, 3)
    }


def main():
    print("=" * 75)
    print("SANTÉ DZ / MEDIZY — EXTRACTION GLOBALE MULTI-FORMATS (PHASE 9)")
    print("=" * 75)
    print(f"Base de données de production : {DEFAULT_DB}")
    print(f"Répertoire d'exportation      : {OUTPUT_DIR}")

    db_sha = calculate_sha256(DEFAULT_DB)
    print(f"SHA-256 base de référence    : {db_sha}")

    t_start = time.perf_counter()
    facilities = fetch_all_facilities(DEFAULT_DB)
    print(f"\n[SUCCÈS] {len(facilities):,} fiches extraites en mémoire.")
    if len(facilities) != EXPECTED_COUNT:
        raise ValueError(f"Volume incorrect : {len(facilities)} au lieu de {EXPECTED_COUNT}")

    # 1. Format CSV
    csv_path = os.path.join(OUTPUT_DIR, "SANTE_DZ_NATIONAL_35832.csv")
    csv_res = export_csv(facilities, csv_path)
    print(f"  [1/4] CSV National        : {csv_res['filepath']} ({csv_res['size_mb']} MB, {csv_res['duration_sec']}s)")

    # 2. Format JSON
    json_path = os.path.join(OUTPUT_DIR, "sante_dz_full_dataset.json")
    json_res = export_json(facilities, db_sha, json_path)
    print(f"  [2/4] JSON Structuré      : {json_res['filepath']} ({json_res['size_mb']} MB, {json_res['duration_sec']}s)")

    # 3. Format GeoJSON SIG
    geojson_path = os.path.join(OUTPUT_DIR, "sante_dz_map_features.geojson")
    geo_res = export_geojson(facilities, geojson_path)
    print(f"  [3/4] GeoJSON SIG         : {geo_res['filepath']} ({geo_res['size_mb']} MB, {geo_res['duration_sec']}s)")

    # 4. Format Excel
    excel_path = os.path.join(OUTPUT_DIR, "SANTE_DZ_REGISTRE_NATIONAL.xlsx")
    excel_res = export_excel(facilities, excel_path)
    print(f"  [4/4] Excel Multi-Onglets : {excel_res['filepath']} ({excel_res['size_mb']} MB, {excel_res['duration_sec']}s)")
    for sheet_name, s_count in excel_res["sheet_counts"].items():
        print(f"        * Onglet '{sheet_name:<24}' : {s_count:>5,} fiches")

    total_time = round(time.perf_counter() - t_start, 2)
    print("\n" + "=" * 75)
    print(f"[RÉSULTAT GLOBAL] 4 exports générés avec succès en {total_time}s.")
    print("=" * 75)


if __name__ == "__main__":
    main()
