import sqlite3
import pandas as pd
import re

print("1. Loading raw Google Maps CSV...")
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

print(f"Loaded {len(lat_lon_map)} place_ids.")

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Temporary table for fast bulk update
c.execute("DROP TABLE IF EXISTS tmp_gmaps_coords")
c.execute("CREATE TABLE tmp_gmaps_coords (place_id TEXT PRIMARY KEY, lat REAL, lon REAL)")

rows_to_insert = [(pid, lat, lon) for pid, (lat, lon) in lat_lon_map.items()]
c.executemany("INSERT INTO tmp_gmaps_coords VALUES (?, ?, ?)", rows_to_insert)
conn.commit()
print("Inserted into temporary table.")

# Update facilities from tmp_gmaps_coords
c.execute("""
    UPDATE facilities 
    SET latitude = (SELECT t.lat FROM tmp_gmaps_coords t WHERE t.place_id = facilities.place_id),
        longitude = (SELECT t.lon FROM tmp_gmaps_coords t WHERE t.place_id = facilities.place_id)
    WHERE place_id IN (SELECT place_id FROM tmp_gmaps_coords)
""")
print(f"Updated facilities table: {c.rowcount} rows.")
conn.commit()

c.execute("DROP TABLE tmp_gmaps_coords")
conn.commit()

# Rebuild spatial rtree index
print("Rebuilding spatial index...")
c.execute("DELETE FROM facilities_rtree")
c.execute("""
    INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
    SELECT id, latitude, latitude, longitude, longitude FROM facilities
""")
print(f"Rtree rebuilt with {c.rowcount} rows.")
conn.commit()
conn.close()
print("FAST SYNC COMPLETE!")

