import sqlite3
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Get the 32 official communes of Mostaganem
c.execute("SELECT nom_fr, latitude, longitude FROM communes WHERE wilaya_code = '27'")
official_communes = c.fetchall()
print(f"Loaded {len(official_communes)} communes for Mostaganem.")

# Facilities in Mostaganem
c.execute("SELECT id, nom, commune, latitude, longitude FROM facilities WHERE wilaya_code = '27'")
facilities = c.fetchall()
print(f"Total facilities in Mostaganem: {len(facilities)}")

updated = 0
reassigned = 0
commune_stats = {}

for f_id, nom, current_commune, lat, lon in facilities:
    # Do not reassign Sidi Ali or Hadjadj or Sidi-Lakhdar which are manually verified
    if current_commune in ('Sidi Ali', 'Hadjadj', 'Sidi-Lakhdar'):
        commune_stats[current_commune] = commune_stats.get(current_commune, 0) + 1
        continue

    # Find nearest commune by GPS
    best_commune = 'Mostaganem'
    min_dist = 999999.0
    for com_fr, com_lat, com_lon in official_communes:
        if com_lat and com_lon and lat and lon:
            d = haversine(lat, lon, com_lat, com_lon)
            if d < min_dist:
                min_dist = d
                best_commune = com_fr

    if best_commune != current_commune:
        c.execute("UPDATE facilities SET commune = ? WHERE id = ?", (best_commune, f_id))
        reassigned += 1
    
    commune_stats[best_commune] = commune_stats.get(best_commune, 0) + 1
    updated += 1

conn.commit()
print(f"\nReassigned {reassigned} facilities across the 32 official communes.")
print("\n--- NEW DISTRIBUTION ACROSS MOSTAGANEM COMMUNES ---")
for com, cnt in sorted(commune_stats.items(), key=lambda x: -x[1]):
    print(f"  {com}: {cnt} structures")

