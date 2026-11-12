import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check OSM records: how were they imported and where are their coordinates?
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, wilaya FROM facilities WHERE source LIKE '%OpenStreetMap%' LIMIT 30")
rows = c.fetchall()
print(f"OSM records sample (out of ~6000):")
for r in rows:
    print(r)

conn.close()

