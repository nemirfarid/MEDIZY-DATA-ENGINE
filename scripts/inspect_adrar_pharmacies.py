import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()

c.execute("SELECT id, nom, adresse, latitude, longitude, google_maps_url FROM places WHERE wilaya LIKE '%Adrar%' AND categorie_recherche = 'pharmacie' LIMIT 30")
rows = c.fetchall()
print(f"Sample of 82 pharmacies in Adrar in medizy_scraper.db:")
for r in rows:
    print(f"  {r[1]} | Coords: ({r[3]}, {r[4]}) | URL: {r[5]}")

conn.close()

