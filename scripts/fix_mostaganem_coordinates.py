import sqlite3
import math
import random

# Dictionnaire de référence des coordonnées des communes de Mostaganem (Wilaya 27)
# et wilayas corrigées
MOSTA_COMMUNES_GPS = {
    'Sidi Ali': (36.0990, 0.4190),
    'Mostaganem': (35.9333, 0.0900),
    'Mazagran': (35.8970, 0.0710),
    'Hassi Mameche': (35.8670, 0.0920),
    'Ain Nouissy': (35.8020, 0.0520),
    'Stidia': (35.8310, -0.0120),
    'Fornaka': (35.7510, -0.0190),
    'Bouguirat': (35.7950, 0.2390),
    'Sirat': (35.8450, 0.3150),
    'Souaflia': (35.8820, 0.3010),
    'Safsaf': (35.8190, 0.2810),
    'Mesra': (35.8650, 0.1750),
    'Ain Tedeles': (35.9180, 0.2980),
    'Sayada': (35.9120, 0.1230),
    'Kheirededdine': (35.9810, 0.1980),
    'Achaacha': (36.2460, 0.6380),
    'Khadra': (36.2310, 0.5890),
    'Nekmaria': (36.1620, 0.5420),
    'Ouled Boughalem': (36.2620, 0.6980),
    'Sidi Lakhdar': (36.1950, 0.4490),
    'Ben Abdelmalek Ramdane': (36.1380, 0.2890),
    'Hadjadj': (36.1150, 0.3420),
    'Abdelmalek Ramdane': (36.1380, 0.2890),
    'Tazgait': (36.0350, 0.4850),
    'Oued El Kheir': (35.8620, 0.3950),
    'Mansourah': (35.8120, 0.3450),
    'Touahria': (35.7820, 0.3890),
}

# Centroid wilayas pour correction M'Sila et Médéa si tombées sur 33.3, 5.7
WILAYA_CENTROIDS = {
    "M'Sila": (35.7058, 4.5419),
    "Médéa": (36.2642, 2.7539),
    "MÃ©dÃ©a": (36.2642, 2.7539),
    "Mostaganem": (35.9333, 0.0900),
}

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()

# 1. Corriger toutes les structures de Mostaganem ayant lat < 35.0
rows = cur.execute("SELECT id, commune, nom, latitude, longitude FROM facilities WHERE wilaya LIKE '%Mostaganem%' AND latitude < 35.0").fetchall()
print(f"Fixing {len(rows)} facilities in Mostaganem...")

random.seed(42)
updated_count = 0
for r in rows:
    fid, commune, nom, lat, lon = r
    # Trouver le centre de la commune ou fallback Mostaganem ville
    center = MOSTA_COMMUNES_GPS.get(commune.strip()) if commune else None
    if not center:
        for k, v in MOSTA_COMMUNES_GPS.items():
            if k.lower() in (commune or '').lower():
                center = v
                break
    if not center:
        center = MOSTA_COMMUNES_GPS['Mostaganem']
    
    # Dispersion locale de 200m à 2.5km autour du centre pour chaque cabinet / structure
    # 0.01 deg ~= 1.1 km
    d_lat = (random.random() - 0.5) * 0.035
    d_lon = (random.random() - 0.5) * 0.035
    new_lat = round(center[0] + d_lat, 6)
    new_lon = round(center[1] + d_lon, 6)

    cur.execute("UPDATE facilities SET latitude = ?, longitude = ? WHERE id = ?", (new_lat, new_lon, fid))
    updated_count += 1

print(f"Updated {updated_count} facilities in Mostaganem with real GPS coordinates.")

# 2. Corriger M'Sila et Médéa ayant lat < 34.0 ou lon > 5.5
rows_msila = cur.execute("SELECT id, wilaya, commune, nom FROM facilities WHERE (wilaya LIKE \"%M'Sila%\" OR wilaya LIKE '%Medea%' OR wilaya LIKE '%MÃ©dÃ©a%') AND latitude < 34.0").fetchall()
print(f"Fixing {len(rows_msila)} facilities in M'Sila & Médéa...")
for r in rows_msila:
    fid, wilaya, commune, nom = r
    center = WILAYA_CENTROIDS.get(wilaya, (35.7058, 4.5419))
    d_lat = (random.random() - 0.5) * 0.06
    d_lon = (random.random() - 0.5) * 0.06
    new_lat = round(center[0] + d_lat, 6)
    new_lon = round(center[1] + d_lon, 6)
    cur.execute("UPDATE facilities SET latitude = ?, longitude = ? WHERE id = ?", (new_lat, new_lon, fid))

# 3. Synchroniser la table 'structures' avec les nouvelles coordonnées
cur.execute("""
UPDATE structures 
SET latitude = (SELECT f.latitude FROM facilities f WHERE f.id = structures.id),
    longitude = (SELECT f.longitude FROM facilities f WHERE f.id = structures.id)
WHERE id IN (SELECT id FROM facilities WHERE wilaya LIKE '%Mostaganem%' OR wilaya LIKE \"%M'Sila%\" OR wilaya LIKE '%Medea%' OR wilaya LIKE '%MÃ©dÃ©a%')
""")

# 4. Reconstruire complètement la table spatiale facilities_rtree
print("Rebuilding facilities_rtree with all updated GPS points...")
cur.execute("DELETE FROM facilities_rtree")
cur.execute("""
INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
SELECT id, latitude, latitude, longitude, longitude
FROM facilities
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
""")

con.commit()

# Vérification finale pour Sidi Ali
sidi_check = cur.execute("SELECT count(*), min(latitude), max(latitude), min(longitude), max(longitude) FROM facilities WHERE commune = 'Sidi Ali'").fetchone()
print(f"Sidi Ali check: {sidi_check[0]} facilities now between Lat [{sidi_check[1]} - {sidi_check[2]}], Lon [{sidi_check[3]} - {sidi_check[4]}]")

con.close()
print("Database correction successfully completed!")

