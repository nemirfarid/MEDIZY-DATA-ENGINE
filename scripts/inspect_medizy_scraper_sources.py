import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()

# Check sources of places in medizy_scraper.db
c.execute("SELECT source, count(1) FROM places GROUP BY source")
print("Sources of places in medizy_scraper.db:", c.fetchall())

# Check coordinates of Adrar places
c.execute("SELECT id, nom, latitude, longitude, google_maps_url, source FROM places WHERE wilaya LIKE '%Adrar%' LIMIT 10")
for r in c.fetchall():
    print("  ", r)

conn.close()

