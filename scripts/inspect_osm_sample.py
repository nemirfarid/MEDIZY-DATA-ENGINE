import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check sample of OpenStreetMap National
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, wilaya FROM facilities WHERE source = 'OpenStreetMap National' LIMIT 20")
for r in c.fetchall():
    print(r)

# Check sample of Google Maps Sidi Ali Test
print("\nGoogle Maps Sidi Ali Test:")
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, wilaya FROM facilities WHERE source = 'Google Maps Sidi Ali Test'")
for r in c.fetchall():
    print(r)

conn.close()

