import sqlite3
import pandas as pd
import re

print("Loading raw Google Maps CSV...")
df = pd.read_csv('C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv', low_memory=False)

lat_lon_map = {}
for idx, row in df.iterrows():
    pid = str(row.get('place_id', ''))
    link = str(row.get('link', ''))
    m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', link)
    if m and pid:
        lat = float(m.group(1))
        lon = float(m.group(2))
        lat_lon_map[pid] = (lat, lon)

print(f"Total entries in Google Maps link map: {len(lat_lon_map)}")

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Update all records that have a place_id with exact Google Maps coordinates
updates = []
for pid, (lat, lon) in lat_lon_map.items():
    updates.append((lat, lon, pid))

print("Applying exact coordinates update to database...")
c.executemany("UPDATE facilities SET latitude = ?, longitude = ? WHERE place_id = ?", updates)
print(f"Updated {c.rowcount} records in facilities!")

conn.commit()

# Rebuild spatial rtree index
print("Rebuilding facilities_rtree index...")
c.execute("DELETE FROM facilities_rtree")
c.execute("""
    INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
    SELECT id, latitude, latitude, longitude, longitude FROM facilities
""")
print(f"Rebuilt spatial index with {c.rowcount} records.")

conn.commit()
conn.close()
print("Synchronization with Google Maps exact coordinates complete!")

