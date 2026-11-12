import sqlite3
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 1. Load official communes of Wilaya 02 from medizy_scraper.db
conn_scraper = sqlite3.connect('medizy_scraper.db')
c_scraper = conn_scraper.cursor()
c_scraper.execute("SELECT nom_fr, nom_ar, latitude, longitude FROM communes WHERE wilaya_code = '02'")
official_communes = c_scraper.fetchall()
print(f"Loaded {len(official_communes)} official communes for Chlef.")

# 2. Check facilities in sante_dz_bundled.db
conn_target = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_target = conn_target.cursor()
c_target.execute("SELECT id, nom, commune, categorie, latitude, longitude FROM facilities WHERE wilaya_code = '02'")
facilities = c_target.fetchall()
print(f"Total facilities in Chlef currently: {len(facilities)}")

updated = 0
category_counts = {}
commune_counts = {}

for fac_id, nom, current_commune, categorie, lat, lon in facilities:
    # Find nearest official commune
    best_commune = None
    min_dist = 999999.0
    for com_fr, com_ar, com_lat, com_lon in official_communes:
        # If commune matches by name directly
        if current_commune and current_commune.lower().strip() == com_fr.lower().strip():
            best_commune = com_fr
            min_dist = 0
            break
        
        # Spatial distance
        if com_lat and com_lon and lat and lon:
            d = haversine(lat, lon, com_lat, com_lon)
            if d < min_dist:
                min_dist = d
                best_commune = com_fr
    
    if not best_commune:
        best_commune = "Chlef"
            
    # Update facility with official commune name
    c_target.execute("UPDATE facilities SET commune = ? WHERE id = ?", (best_commune, fac_id))
    updated += 1
    
    commune_counts[best_commune] = commune_counts.get(best_commune, 0) + 1
    category_counts[categorie] = category_counts.get(categorie, 0) + 1

conn_target.commit()

# Rebuild FTS
c_target.execute("INSERT INTO facilities_fts(facilities_fts) VALUES('rebuild')")
conn_target.commit()

print(f"\n--- NORMALIZATION COMPLETED: {updated} facilities updated ---")
print(f"\nBreakdown across the {len(commune_counts)} official communes:")
for com, cnt in sorted(commune_counts.items(), key=lambda x: -x[1]):
    print(f"  - {com}: {cnt} structures")

print(f"\nBreakdown by Category in Wilaya 02 (Chlef):")
for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
    print(f"  - {cat}: {cnt} structures")
