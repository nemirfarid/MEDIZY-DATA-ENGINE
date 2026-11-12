import sqlite3
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

print("=== DEEP COMMUNAL REMAPPING FOR ALL 58 WILAYAS (1,541 OFFICIAL COMMUNES) ===")

conn_scraper = sqlite3.connect('medizy_scraper.db')
c_scraper = conn_scraper.cursor()

# 1. Load all 1541 official communes
c_scraper.execute("SELECT wilaya_code, nom_fr, nom_ar, latitude, longitude FROM communes")
all_communes = c_scraper.fetchall()
print(f"Total official communes loaded: {len(all_communes)}")

# Group by wilaya_code
communes_by_wilaya = {}
for w_code, c_fr, c_ar, lat, lon in all_communes:
    w_code_str = str(w_code).zfill(2)
    if w_code_str not in communes_by_wilaya:
        communes_by_wilaya[w_code_str] = []
    if lat is not None and lon is not None:
        communes_by_wilaya[w_code_str].append((c_fr, c_ar, lat, lon))

print(f"Grouped into {len(communes_by_wilaya)} wilayas.")

conn_target = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_target = conn_target.cursor()

c_target.execute("SELECT id, wilaya_code, wilaya, commune, latitude, longitude FROM facilities")
facilities = c_target.fetchall()
print(f"Total facilities to examine: {len(facilities)}")

updated = 0
reassigned_to_exact_commune = 0
batch_updates = []

for fac_id, w_code, w_name, current_commune, lat, lon in facilities:
    w_code_str = str(w_code).zfill(2) if w_code else '16'
    wilaya_comms = communes_by_wilaya.get(w_code_str, [])
    
    if not wilaya_comms or lat is None or lon is None:
        continue
        
    # Check if current commune is already an exact match to one of the official communes of this wilaya
    exact_match = None
    if current_commune and current_commune.lower().strip() != (w_name or '').lower().strip():
        for c_fr, c_ar, c_lat, c_lon in wilaya_comms:
            if current_commune.lower().strip() == c_fr.lower().strip():
                exact_match = c_fr
                break
    
    if exact_match:
        # Keep exact valid commune name
        best_commune = exact_match
    else:
        # Compute exact nearest commune by GPS
        min_dist = 999999.0
        best_commune = wilaya_comms[0][0]
        for c_fr, c_ar, c_lat, c_lon in wilaya_comms:
            d = haversine(lat, lon, c_lat, c_lon)
            if d < min_dist:
                min_dist = d
                best_commune = c_fr
        reassigned_to_exact_commune += 1
        
    batch_updates.append((best_commune, fac_id))
    updated += 1
    
    if len(batch_updates) >= 5000:
        c_target.executemany("UPDATE facilities SET commune = ? WHERE id = ?", batch_updates)
        conn_target.commit()
        batch_updates = []
        print(f"  Processed {updated} / {len(facilities)}...")

if batch_updates:
    c_target.executemany("UPDATE facilities SET commune = ? WHERE id = ?", batch_updates)
    conn_target.commit()

c_target.execute("SELECT COUNT(DISTINCT commune), COUNT(DISTINCT wilaya_code), COUNT(*) FROM facilities")
distinct_comms, distinct_wilayas, total_facs = c_target.fetchone()

print(f"\n--- REMAPPING COMPLETED ---")
print(f"Total facilities updated: {updated}")
print(f"Facilities mapped from general Wilaya to exact Commune: {reassigned_to_exact_commune}")
print(f"Total active distinct communes represented: {distinct_comms} across {distinct_wilayas} Wilayas")

# Rebuild search & spatial indices
print("Rebuilding FTS & R-Tree...")
c_target.execute("INSERT INTO facilities_fts(facilities_fts) VALUES('rebuild')")
conn_target.commit()
print("Done!")
