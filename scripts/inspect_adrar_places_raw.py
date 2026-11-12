import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()

c.execute("SELECT id, nom, adresse, categorie_recherche, commune, latitude, longitude, google_maps_url FROM places WHERE wilaya LIKE '%Adrar%' LIMIT 25")
rows = c.fetchall()
print(f"Sample of 406 places already scraped for Adrar in medizy_scraper.db:")
for r in rows:
    print(r)

conn.close()

