import sqlite3
import math

conn_src = sqlite3.connect('medizy_scraper.db')
c_src = conn_src.cursor()

conn_dst = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_dst = conn_dst.cursor()

# Official 16 Communes of Wilaya 01 (Adrar) with exact coordinates
COMMUNES_ADRAR = [
    ("Adrar", 27.8742, -0.2939),
    ("Tamest", 27.6333, -0.2667),
    ("Reggane", 26.7197, 0.1714),
    ("In Zghmir", 27.1167, -0.1167),
    ("Tit", 26.9667, -0.0167),
    ("Tsabit", 28.3333, -0.2500),
    ("Timmi", 27.8437, -0.2833),
    ("Ouled Ahmed Timmi", 27.7667, -0.2667),
    ("Bouda", 27.9667, -0.4167),
    ("Aoulef", 26.9667, 1.0833),
    ("Timekten", 27.0500, 1.3000),
    ("Tamantit", 27.7667, -0.2667),
    ("Fenoughil", 27.6500, -0.3000),
    ("Sali", 26.9000, -0.1667),
    ("Sebaa", 28.1833, -0.3500),
    ("Akabli", 26.7167, 1.3667)
]

def find_nearest_commune(lat, lon):
    best_c = "Adrar"
    min_d = 999999
    for name, clat, clon in COMMUNES_ADRAR:
        d = (lat - clat)**2 + (lon - clon)**2
        if d < min_d:
            min_d = d
            best_c = name
    return best_c

c_src.execute("""
    SELECT nom, adresse, telephone, note, nombre_avis, latitude, longitude, google_maps_url, type_google, categorie_recherche, commune
    FROM places 
    WHERE wilaya LIKE '%Adrar%' 
      AND latitude IS NOT NULL AND longitude IS NOT NULL
      AND latitude >= 25.0 AND latitude <= 30.0
      AND longitude >= -2.5 AND longitude <= 2.5
""")
adrar_places = c_src.fetchall()
print(f"Total authentic Adrar places to process: {len(adrar_places)}")

added = 0
updated = 0
for p in adrar_places:
    nom, adresse, tel, note, avis, lat, lon, gmaps_url, type_google, cat_search, comm_orig = p
    
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
    commune_assigned = comm_orig.strip() if comm_orig and comm_orig.strip() else find_nearest_commune(lat, lon)
    
    # Check if exists in bundled DB
    c_dst.execute("""
        SELECT id FROM facilities 
        WHERE (nom = ? OR (abs(latitude - ?) < 0.0003 AND abs(longitude - ?) < 0.0003))
    """, (nom, lat, lon))
    exists = c_dst.fetchone()
    
    if exists:
        c_dst.execute("""
            UPDATE facilities 
            SET wilaya = 'Adrar', wilaya_code = '01', commune = ?, categorie = ?, latitude = ?, longitude = ?,
                adresse = COALESCE(NULLIF(?, ''), adresse), telephone = COALESCE(NULLIF(?, ''), telephone),
                site_web = COALESCE(NULLIF(?, ''), site_web), source = 'Google Maps Verified'
            WHERE id = ?
        """, (commune_assigned, cat_final, lat, lon, adresse, tel, gmaps_url, exists[0]))
        updated += 1
    else:
        c_dst.execute("""
            INSERT INTO facilities (nom, categorie, wilaya, wilaya_code, commune, adresse, telephone, note, nombre_avis, latitude, longitude, site_web, source)
            VALUES (?, ?, 'Adrar', '01', ?, ?, ?, ?, ?, ?, ?, ?, 'Google Maps Verified')
        """, (nom, cat_final, commune_assigned, adresse, tel, note, avis, lat, lon, gmaps_url))
        added += 1

conn_dst.commit()
print(f"Adrar processing complete: {added} new facilities added, {updated} updated with authentic Google Maps coordinates.")

# Rebuild spatial rtree
c_dst.execute("DELETE FROM facilities_rtree")
c_dst.execute("""
    INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
    SELECT id, latitude, latitude, longitude, longitude FROM facilities
""")
conn_dst.commit()

# Print breakdown by commune and category
print("\n--- SYNTHÈSE WILAYA 01 (ADRAR) ---")
c_dst.execute("SELECT commune, count(1) FROM facilities WHERE wilaya_code = '01' GROUP BY commune ORDER BY count(1) DESC")
for com, cnt in c_dst.fetchall():
    print(f"  * Commune '{com}' : {cnt} structures de santé réelles")

print("\nRépartition par catégorie à Adrar :")
c_dst.execute("SELECT categorie, count(1) FROM facilities WHERE wilaya_code = '01' GROUP BY categorie ORDER BY count(1) DESC")
for cat, cnt in c_dst.fetchall():
    print(f"  - {cat} : {cnt}")

conn_src.close()
conn_dst.close()

