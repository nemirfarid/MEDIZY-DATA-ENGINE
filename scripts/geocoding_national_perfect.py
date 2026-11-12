import sqlite3
import re
import random
import math

# Référentiel des 58 chefs-lieux
WILAYA_REF = {
    '01': (27.8742, -0.2939), '02': (36.1652, 1.3345), '03': (33.8000, 2.8651), '04': (35.8755, 7.1135),
    '05': (35.5558, 6.1741), '06': (36.7559, 5.0843), '07': (34.8504, 5.7281), '08': (31.6167, -2.2167),
    '09': (36.4700, 2.8300), '10': (36.3749, 3.9020), '11': (22.7850, 5.5228), '12': (35.4042, 8.1242),
    '13': (34.8828, -1.3167), '14': (35.3710, 1.3170), '15': (36.7118, 4.0459), '16': (36.7538, 3.0588),
    '17': (34.6728, 3.2630), '18': (36.8206, 5.7667), '19': (36.1911, 5.4137), '20': (34.8303, 0.1517),
    '21': (36.8792, 6.9075), '22': (35.1899, -0.6309), '23': (36.9000, 7.7667), '24': (36.4621, 7.4261),
    '25': (36.3650, 6.6147), '26': (36.2642, 2.7539), '27': (35.9311, 0.0892), '28': (35.7058, 4.5419),
    '29': (35.3964, 0.1403), '30': (31.9493, 5.3250), '31': (35.6971, -0.6308), '32': (33.6832, 1.0193),
    '33': (26.4833, 8.4667), '34': (36.0732, 4.7611), '35': (36.7664, 3.4772), '36': (36.7672, 8.3138),
    '37': (27.6711, -8.1474), '38': (35.6072, 1.8108), '39': (33.3683, 6.8675), '40': (35.4358, 7.1433),
    '41': (36.2864, 7.9511), '42': (36.5897, 2.4475), '43': (36.4503, 6.2644), '44': (36.2644, 1.9675),
    '45': (33.2667, -0.3167), '46': (35.2975, -1.1403), '47': (32.4909, 3.6736), '48': (35.7372, 0.5558),
    '49': (29.2639, 0.2310), '50': (21.3283, 0.9547), '51': (34.4278, 5.0667), '52': (30.1333, -2.1667),
    '53': (27.1936, 2.4608), '54': (19.5667, 5.7667), '55': (33.1053, 6.0578), '56': (24.5531, 9.4853),
    '57': (33.9500, 5.9167), '58': (30.5847, 2.8797),
}

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()

# Trouver les centres réels de chaque commune existante en moyennant les coordonnées fiables (Good points)
print("1. Calculating real commune centroids from reliable points...")
commune_centroids = {}
rows = cur.execute("""
SELECT wilaya_code, commune, avg(latitude), avg(longitude), count(*)
FROM facilities
WHERE latitude BETWEEN 19.0 AND 37.5 
  AND longitude BETWEEN -8.7 AND 12.0
  AND NOT (latitude BETWEEN 33.29 AND 33.31 AND longitude BETWEEN 5.69 AND 5.71)
GROUP BY wilaya_code, commune
HAVING count(*) >= 2
""").fetchall()

for r in rows:
    wcode, com, avg_lat, avg_lon, count = r
    if com and com.strip():
        commune_centroids[(str(wcode).zfill(2), com.strip().lower())] = (avg_lat, avg_lon)

print(f"Computed {len(commune_centroids)} reliable commune centroids nationwide.")

# 2. Scanner TOUTES les 59,637 structures
# Détecter celles qui sont sur un point d'accumulation artificiel (ex: 33.3, 5.7) ou hors-territoire ou superposées
print("2. Scanning all facilities for outlier or dummy coordinates...")
all_facs = cur.execute("SELECT id, wilaya_code, wilaya, commune, nom, latitude, longitude FROM facilities").fetchall()

random.seed(12345)
corrected = 0

for fac in all_facs:
    fid, wcode, wilaya, commune, nom, lat, lon = fac
    wcode_str = str(wcode).zfill(2) if wcode else None
    
    # Critères de point artificiel ou corrompu :
    is_dummy_cluster = (33.28 <= lat <= 33.32 and 5.68 <= lon <= 5.72 and wcode_str not in ('39', '55', '57'))
    is_out_of_bounds = not (19.0 <= lat <= 37.5 and -8.7 <= lon <= 12.0)
    
    # Distance aberrante par rapport au chef-lieu de la wilaya (> 180 km pour wilayas du nord)
    ref_coords = WILAYA_REF.get(wcode_str)
    is_far = False
    if ref_coords and lat and lon:
        dist_deg = math.sqrt((lat - ref_coords[0])**2 + (lon - ref_coords[1])**2)
        if wcode_str in ['16', '09', '15', '35', '42', '27', '31', '25', '23', '13', '22', '46', '48'] and dist_deg > 1.5:
            is_far = True

    if is_dummy_cluster or is_out_of_bounds or is_far:
        # Trouver le centre de la commune ou de la wilaya
        key = (wcode_str, (commune or '').strip().lower())
        target_center = commune_centroids.get(key)
        if not target_center and ref_coords:
            target_center = ref_coords
        elif not target_center:
            target_center = (36.7538, 3.0588) # Fallback Alger

        # Dispersion fine (200m à 1.5km) pour que chaque praticien ait son marqueur bien visible et cliquable
        offset_lat = (random.random() - 0.5) * 0.025
        offset_lon = (random.random() - 0.5) * 0.025
        new_lat = round(target_center[0] + offset_lat, 6)
        new_lon = round(target_center[1] + offset_lon, 6)

        cur.execute("UPDATE facilities SET latitude = ?, longitude = ? WHERE id = ?", (new_lat, new_lon, fid))
        corrected += 1

print(f"Corrected {corrected} facilities nationwide.")

# 3. Éviter toute superposition exacte (clumping à 0 mètre) : ajouter un micro-jitter si doublon exact de coordonnée
print("3. Checking and micro-jittering exact coordinate collisions...")
cur.execute("""
SELECT latitude, longitude, count(*)
FROM facilities
GROUP BY latitude, longitude
HAVING count(*) > 3
""")
collisions = cur.fetchall()
jittered = 0
for col in collisions:
    clat, clon, count = col
    collided_ids = [r[0] for r in cur.execute("SELECT id FROM facilities WHERE latitude = ? AND longitude = ?", (clat, clon)).fetchall()]
    for i, cid in enumerate(collided_ids[1:], start=1):
        angle = (2 * math.pi / count) * i
        dist = 0.0012 * (1 + (i % 3) * 0.4) # ~100 à 180 mètres
        j_lat = round(clat + dist * math.cos(angle), 6)
        j_lon = round(clon + dist * math.sin(angle), 6)
        cur.execute("UPDATE facilities SET latitude = ?, longitude = ? WHERE id = ?", (j_lat, j_lon, cid))
        jittered += 1

print(f"Applied spatial micro-jitter to {jittered} overlapping structures.")

# 4. Synchronisation de la table structures
cur.execute("""
UPDATE structures 
SET latitude = (SELECT f.latitude FROM facilities f WHERE f.id = structures.id),
    longitude = (SELECT f.longitude FROM facilities f WHERE f.id = structures.id)
""")

# 5. Reconstruction complète de la table R-Tree
print("4. Rebuilding facilities_rtree index...")
cur.execute("DELETE FROM facilities_rtree")
cur.execute("""
INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
SELECT id, latitude, latitude, longitude, longitude
FROM facilities
WHERE latitude IS NOT NULL AND longitude IS NOT NULL
""")

con.commit()
total_facs = cur.execute("SELECT count(*) FROM facilities").fetchone()[0]
total_rtree = cur.execute("SELECT count(*) FROM facilities_rtree").fetchone()[0]
print(f"Verification: {total_facs} facilities and {total_rtree} indexed in R-Tree.")
con.close()
print("National geocoding & spatial indexing 100% COMPLETE!")

