import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT id, place_id, nom, categorie, wilaya, commune, latitude, longitude, site_web, source FROM facilities WHERE source = 'Google Maps Extractor' LIMIT 10")
for r in c.fetchall():
    print(r)

conn.close()

