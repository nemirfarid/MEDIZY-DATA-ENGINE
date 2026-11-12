import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Remove exact duplicates (same lower name, same rounded coords)
c.execute("""
    DELETE FROM facilities
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM facilities
        GROUP BY lower(trim(nom)), round(latitude, 3), round(longitude, 3)
    )
""")
print(f"Deleted exact coordinate duplicates. Rows affected: {c.rowcount}")

conn.commit()

# Rebuild spatial rtree and fts
c.execute("DELETE FROM facilities_rtree")
c.execute("""
    INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
    SELECT id, latitude, latitude, longitude, longitude FROM facilities
""")
print("Rebuilt facilities_rtree.")

conn.commit()
conn.close()

