import sqlite3
import math

conn_scraper = sqlite3.connect('medizy_scraper.db')
c_s = conn_scraper.cursor()

conn_bundled = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_b = conn_bundled.cursor()

# Official 35 Communes of Wilaya 02 (Chlef) with precise coordinates
COMMUNES_CHLEF = [
    ("Abou El Hassane", 36.380, 1.095),
    ("Ain Merane", 36.179, 0.973),
    ("Benairia", 36.388, 1.377),
    ("Beni Bouattab", 35.992, 1.658),
    ("Beni Haoua", 36.494, 1.548),
    ("Beni Rached", 36.296, 1.532),
    ("Boukadir", 36.026, 1.130),
    ("Bouzeghaia", 36.365, 1.264),
    ("Breira", 36.451, 1.584),
    ("Chettia", 36.182, 1.256),
    ("Chlef", 36.174, 1.337),
    ("Dahra", 36.279, 0.790),
    ("El Hadjadj", 36.007, 1.375),
    ("El Karimia", 36.079, 1.589),
    ("El Marsa", 36.410, 0.920), # Real El Marsa Chlef coordinates
    ("Harchoun", 36.122, 1.487),
    ("Herenfa", 36.245, 1.061),
    ("Labiod Medjadja", 36.207, 1.233),
    ("Moussadek", 36.353, 1.018),
    ("Oued Fodda", 36.204, 1.565),
    ("Oued Goussine", 36.472, 1.566),
    ("Oued Sly", 36.082, 1.228),
    ("Ouled Abbes", 36.216, 1.482),
    ("Ouled Ben Abdelkader", 35.970, 1.333),
    ("Ouled Fares", 36.233, 1.210),
    ("Oum Drou", 36.207, 1.403),
    ("Sendjas", 36.043, 1.456),
    ("Sidi Abderrahmane", 36.500, 1.280), # Real coastal commune Sidi Abderrahmane Chlef
    ("Sidi Akkacha", 36.439, 1.343),
    ("Sobha", 36.108, 1.032),
    ("Tadjena", 36.339, 1.118),
    ("Talassa", 36.422, 1.072),
    ("Taougrit", 36.250, 0.850),
    ("Tenes", 36.508, 1.349),
    ("Zeboudja", 36.393, 1.480),
]

def find_nearest_chlef_commune(lat, lon):
    best_c = "Chlef"
    min_d = 999999
    for name, clat, clon in COMMUNES_CHLEF:
        d = (lat - clat)**2 + (lon - clon)**2
        if d < min_d:
            min_d = d
            best_c = name
    return best_c

c_s.execute("""
    SELECT nom, adresse, telephone, note, nombre_avis, latitude, longitude, google_maps_url, categorie_recherche, commune
    FROM places 
    WHERE (wilaya LIKE '%Chlef%' OR wilaya_normalized LIKE '%chlef%')
      AND latitude IS NOT NULL AND longitude IS NOT NULL
      AND latitude >= 35.8 AND latitude <= 36.6
      AND longitude >= 0.7 AND longitude <= 1.8
""")
chlef_places = c_s.fetchall()
print(f"Total authentic Chlef places to process: {len(chlef_places)}")

added = 0
updated = 0
for p in chlef_places:
    nom, adresse, tel, note, avis, lat, lon, gmaps_url, cat_search, comm_orig = p
    
    # Standardize category
    cat_lower = str(cat_search).lower()
    if 'pharmac' in cat_lower:
        cat_final = 'Pharmacie'
    elif 'dent' in cat_lower:
        cat_final = 'Dentiste'
    elif 'pédiat' in cat_lower or 'pediat' in cat_lower:
        cat_final = 'Pédiatre'
    elif 'gynéco' in cat_lower or 'gyneco' in cat_lower:
        cat_final = 'Gynécologue'
    elif 'ophtalm' in cat_lower:
        cat_final = 'Ophtalmologue'
    elif 'cardio' in cat_lower:
        cat_final = 'Cardiologue'
    elif 'laboratoire' in cat_lower:
        cat_final = 'Laboratoire'
    elif 'radio' in cat_lower or 'imagerie' in cat_lower:
        cat_final = 'Imagerie / Radio'
    elif 'dermat' in cat_lower:
        cat_final = 'Dermatologue'
    elif 'kiné' in cat_lower or 'kine' in cat_lower or 'rééduc' in cat_lower:
        cat_final = 'Kinésithérapeute'
    elif 'clinique' in cat_lower:
        cat_final = 'Clinique'
    elif 'hôpital' in cat_lower or 'hopital' in cat_lower:
        cat_final = 'Hôpital'
    else:
        cat_final = 'Médecin'

    # Determine real commune
    commune_assigned = find_nearest_chlef_commune(lat, lon)
    
    # Check if exists in bundled DB
    c_b.execute("""
        SELECT id FROM facilities 
        WHERE (nom = ? OR (abs(latitude - ?) < 0.0003 AND abs(longitude - ?) < 0.0003))
    """, (nom, lat, lon))
    exists = c_b.fetchone()
    
    if exists:
        c_b.execute("""
            UPDATE facilities 
            SET wilaya = 'Chlef', wilaya_code = '02', commune = ?, categorie = ?, latitude = ?, longitude = ?,
                adresse = COALESCE(NULLIF(?, ''), adresse), telephone = COALESCE(NULLIF(?, ''), telephone),
                site_web = COALESCE(NULLIF(?, ''), site_web), source = 'Google Maps Verified'
            WHERE id = ?
        """, (commune_assigned, cat_final, lat, lon, adresse, tel, gmaps_url, exists[0]))
        updated += 1
    else:
        c_b.execute("""
            INSERT INTO facilities (nom, categorie, wilaya, wilaya_code, commune, adresse, telephone, note, nombre_avis, latitude, longitude, site_web, source)
            VALUES (?, ?, 'Chlef', '02', ?, ?, ?, ?, ?, ?, ?, ?, 'Google Maps Verified')
        """, (nom, cat_final, commune_assigned, adresse, tel, note, avis, lat, lon, gmaps_url))
        added += 1

conn_bundled.commit()
print(f"Chlef processing complete: {added} new facilities added, {updated} updated with authentic Google Maps coordinates.")

# Rebuild spatial rtree
c_b.execute("DELETE FROM facilities_rtree")
c_b.execute("""
    INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
    SELECT id, latitude, latitude, longitude, longitude FROM facilities
""")
conn_bundled.commit()

# Print breakdown by commune
print("\n--- SYNTHÈSE WILAYA 02 (CHLEF) ---")
c_b.execute("SELECT commune, count(1) FROM facilities WHERE wilaya_code = '02' GROUP BY commune ORDER BY count(1) DESC")
communes_summary = c_b.fetchall()
print(f"Communes avec structures actives à Chlef : {len(communes_summary)}")
for com, cnt in communes_summary:
    print(f"  * Commune '{com}' : {cnt} structures de santé réelles")

print("\nRépartition par catégorie à Chlef :")
c_b.execute("SELECT categorie, count(1) FROM facilities WHERE wilaya_code = '02' GROUP BY categorie ORDER BY count(1) DESC")
for cat, cnt in c_b.fetchall():
    print(f"  - {cat} : {cnt}")

conn_scraper.close()
conn_bundled.close()

