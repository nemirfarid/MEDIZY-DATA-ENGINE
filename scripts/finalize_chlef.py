import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Remove remaining generic synthetic OSM labels if any
c.execute("DELETE FROM facilities WHERE id IN (72305, 74930)")
print("Removed out-of-boundary generic entries:", c.rowcount)

# Rebuild spatial R-Tree for facilities
c.execute("DELETE FROM facilities_rtree")
c.execute("""
    INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
    SELECT id, latitude, latitude, longitude, longitude FROM facilities
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
""")
conn.commit()

# Final audit for Chlef
c.execute("SELECT COUNT(*), COUNT(DISTINCT commune) FROM facilities WHERE wilaya_code = '02'")
total, communes = c.fetchone()
print(f"Wilaya 02 (Chlef) Final: {total} health structures across {communes} official communes.")

