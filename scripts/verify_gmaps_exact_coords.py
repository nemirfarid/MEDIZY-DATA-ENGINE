import sqlite3
import pandas as pd
import re

print("Loading raw Google Maps CSV...")
df = pd.read_csv('C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv', low_memory=False)
print(f"Total rows in CSV: {len(df)}")

# Extract latitude and longitude from Google Maps link
# URL pattern: !3d(lat)!4d(lon)
lat_lon_map = {}
for idx, row in df.iterrows():
    pid = str(row.get('place_id', ''))
    link = str(row.get('link', ''))
    m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', link)
    if m and pid:
        lat = float(m.group(1))
        lon = float(m.group(2))
        lat_lon_map[pid] = (lat, lon)

print(f"Total place_ids with exact Google Maps coordinates: {len(lat_lon_map)}")

# Connect to database and verify
conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT id, place_id, nom, latitude, longitude FROM facilities WHERE place_id IS NOT NULL AND place_id != ''")
db_records = c.fetchall()
print(f"Checking {len(db_records)} records in DB against Google Maps link...")

discrepancies = 0
for fac_id, pid, nom, lat, lon in db_records:
    if pid in lat_lon_map:
        raw_lat, raw_lon = lat_lon_map[pid]
        # difference in meters approx
        diff_lat = abs(lat - raw_lat)
        diff_lon = abs(lon - raw_lon)
        if diff_lat > 0.0001 or diff_lon > 0.0001:
            discrepancies += 1
            if discrepancies <= 5:
                print(f"Discrepancy for ID {fac_id} ({nom}): DB=({lat}, {lon}) vs GMaps=({raw_lat}, {raw_lon})")

print(f"Total coordinate discrepancies between DB and Google Maps: {discrepancies}")
conn.close()

