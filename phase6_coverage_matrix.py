#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate the final phase6_coverage_matrix.csv with all sources and DB coverage."""
import csv
import sqlite3
from collections import defaultdict
from pathlib import Path

EXPORTS = Path(r"D:\SANTE_DZ_EXPORTS")

WILAYAS = [
    ("Adrar", 1), ("Chlef", 2), ("Laghouat", 3), ("Oum El Bouaghi", 4),
    ("Batna", 5), ("Béjaïa", 6), ("Biskra", 7), ("Béchar", 8),
    ("Blida", 9), ("Bouira", 10), ("Tamanrasset", 11), ("Tébessa", 12),
    ("Tlemcen", 13), ("Tiaret", 14), ("Tizi Ouzou", 15), ("Alger", 16),
    ("Djelfa", 17), ("Jijel", 18), ("Sétif", 19), ("Saïda", 20),
    ("Skikda", 21), ("Sidi Bel Abbès", 22), ("Annaba", 23), ("Guelma", 24),
    ("Constantine", 25), ("Médéa", 26), ("Mostaganem", 27), ("M'Sila", 28),
    ("Mascara", 29), ("Ouargla", 30), ("Oran", 31), ("El Bayadh", 32),
    ("Illizi", 33), ("Bordj Bou Arréridj", 34), ("Boumerdès", 35),
    ("El Tarf", 36), ("Tindouf", 37), ("Tissemsilt", 38), ("El Oued", 39),
    ("Khenchela", 40), ("Souk Ahras", 41), ("Tipaza", 42), ("Mila", 43),
    ("Aïn Defla", 44), ("Naâma", 45), ("Aïn Témouchent", 46),
    ("Ghardaïa", 47), ("Relizane", 48), ("Timimoun", 49),
    ("Bordj Badji Mokhtar", 50), ("Ouled Djellal", 51), ("Béni Abbès", 52),
    ("In Salah", 53), ("In Guezzam", 54), ("Touggourt", 55), ("Djanet", 56),
    ("El M'Ghair", 57), ("El Meniaa", 58),
]

def main():
    # Load MIPH wilaya breakdown
    miph_wilaya = defaultdict(lambda: defaultdict(int))
    miph_path = EXPORTS / "miph_parsed_all.csv"
    with open(miph_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            miph_wilaya[row["wilaya"]][row["type_etab"]] += 1

    # Load MIPH cross-ref results
    matched_by_wilaya = defaultdict(int)
    new_by_wilaya = defaultdict(int)
    with open(EXPORTS / "miph_crossref_matched.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            matched_by_wilaya[row["wilaya"]] += 1
    with open(EXPORTS / "miph_crossref_new.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            new_by_wilaya[row["wilaya"]] += 1

    # Get DB wilaya counts
    conn = sqlite3.connect(r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db")
    cursor = conn.cursor()
    cursor.execute("SELECT wilaya, COUNT(*) FROM places GROUP BY wilaya")
    db_wilaya = {r[0]: r[1] for r in cursor.fetchall()}
    cursor.execute("SELECT COUNT(*) FROM places")
    db_total = cursor.fetchone()[0]

    # Get DB category counts
    cursor.execute("SELECT categorie_recherche, COUNT(*) FROM places WHERE categorie_recherche IS NOT NULL GROUP BY categorie_recherche")
    db_cat = {r[0]: r[1] for r in cursor.fetchall()}

    # Get DB type_google counts
    cursor.execute("SELECT type_google, COUNT(*) FROM places WHERE type_google IS NOT NULL GROUP BY type_google")
    db_type = {r[0]: r[1] for r in cursor.fetchall()}

    conn.close()

    # === Coverage Matrix ===
    matrix_path = EXPORTS / "phase6_coverage_matrix.csv"
    with open(matrix_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Wilaya", "Code", "MIPH PDF", "MIPH matched DB",
                         "MIPH new", "DB entries", "DB GPS", "DB Phone",
                         "DB Address", "DB Website", "DB Note", "Coverage %"])

        for wilaya, code in WILAYAS:
            miph_count = sum(miph_wilaya.get(wilaya, {}).values())
            miph_matched = matched_by_wilaya.get(wilaya, 0)
            miph_new = new_by_wilaya.get(wilaya, 0)
            db_count = db_wilaya.get(wilaya, 0)

            # Get field coverage for this wilaya
            cursor2 = sqlite3.connect(r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db").cursor()
            cursor2.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN latitude IS NOT NULL then 1 ELSE 0 END) as gps,
                    SUM(CASE WHEN telephone IS NOT NULL AND telephone != '' THEN 1 ELSE 0 END) as phone,
                    SUM(CASE WHEN adresse IS NOT NULL AND adresse != '' THEN 1 ELSE 0 END) as addr,
                    SUM(CASE WHEN site_web IS NOT NULL AND site_web != '' THEN 1 ELSE 0 END) as site,
                    SUM(CASE WHEN note IS NOT NULL AND note != '' THEN 1 ELSE 0 END) as note
                FROM places WHERE wilaya = ?
            """, (wilaya,))
            row = cursor2.fetchone()
            if row and row[0]:
                total, gps, phone, addr, site, note = row
                coverage = f"{100*miph_matched/miph_count:.0f}%" if miph_count > 0 else "N/A"
            else:
                total = gps = phone = addr = site = note = 0
                coverage = "N/A"

            writer.writerow([wilaya, f"{code:02d}", miph_count, miph_matched, miph_new,
                            total, gps, phone, addr, site, note, coverage])

        writer.writerow([])
        writer.writerow(["CATÉGORIE / TYPE COMPARISON"])
        writer.writerow(["Type", "MIPH PDF", "GeoAlgeria/sante", "GeoAlgeria/cliniques",
                         "DB (Google Maps)", "Notes"])
        type_rows = [
            ("CHU", 16, 17, 0,
             616, "University hospitals (subset of hôpital category)"),
            ("EPH", 246, 245, 0,
             616, "Public hospitals (shares hôpital category with CHU/EH)"),
            ("EHS+EH+EHU", 105 + 9 + 1, 74, 0,
             1545, "Specialized hospitals (subset of clinique category)"),
            ("EPSP", 273, 259, 137 + 210,
             1360, "Proximity health centers"),
            ("DSP", 58, 0, 0,
             0, "Health ministry offices (not scraped by Google Maps)"),
            ("Institut/Formation", 45, 0, 0,
             0, "Training institutes (not in Google Maps categories)"),
            ("Other structures", 7, 0, 0,
             0, "Agency/National structures"),
            ("Polyclinique (private)", 0, 0, 418,
             254, "Private polyclinics from OSM"),
            ("Clinique privée", 0, 0, 1101,
             1545, "Private clinics from OSM (includes public EHS)"),
            ("Pharmacie", 0, 0, 0,
             2574, "Pharmacies (Google Maps only)"),
            ("Médecin/cabinets", 0, 0, 0,
             3098, "Doctors + clinics (Google Maps only)"),
            ("Laboratoire", 0, 0, 0,
             1353, "Medical labs (Google Maps only)"),
            ("Dentiste/cabinets", 0, 0, 0,
             2668, "Dentists + dental clinics (Google Maps only)"),
        ]
        for row in type_rows:
            writer.writerow(row)

        writer.writerow([])
        writer.writerow(["FIELD ENRICHMENT OPPORTUNITY (MIPH → DB)"])
        writer.writerow(["Field", "MIPH provides", "DB currently missing", "Action"])
        writer.writerow(["Wilaya (official code)", "Numeric code → name mapping",
                         "Some DB wilaya fields are misassigned", "Correct via code_postal"])
        writer.writerow(["Commune", "Postal codes enable geocoding",
                         "~44% of matched entries have no address", "Geocode via postal code"])
        writer.writerow(["Téléphone", "Not in MIPH PDF",
                         "~50% missing in matched DB entries",
                         "Cross-reference tibdz.com, AnnuMed"])
        writer.writerow(["Site web", "Not in MIPH PDF",
                         "~99% missing", "Cross-reference tibdz.com, AnnuMed, GeoAlgeria"])
        writer.writerow(["GPS coordinates", "Postal codes",
                         "~100% present in DB", "MIPH not a gap, but confirms locations"])
        writer.writerow(["Note/Review", "Not in MIPH PDF",
                         "~44% missing", "Cross-reference Google Maps API for ratings"])
        writer.writerow(["Horaires", "Not in MIPH PDF", "100% missing", "Requires Google Maps scraping"])

    print(f"Coverage matrix: {matrix_path}")
    print(f"DB total: {db_total}")
    print(f"MIPH total: {sum(sum(d.values()) for d in miph_wilaya.values())}")
    print(f"MIPH matched: {sum(matched_by_wilaya.values())}")
    print(f"MIPH new: {sum(new_by_wilaya.values())}")


if __name__ == "__main__":
    main()
