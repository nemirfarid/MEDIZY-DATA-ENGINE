import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Search for facilities where coordinates might be suspicious
# 1. Very generic names or suspicious sources
print("Checking OSM vs GMaps coordinates in Mostaganem:")
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, source FROM facilities WHERE wilaya = 'Mostaganem' LIMIT 25")
for r in c.fetchall():
    print(r)

conn.close()

