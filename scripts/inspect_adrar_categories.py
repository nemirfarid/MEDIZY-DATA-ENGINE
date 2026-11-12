import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()

c.execute("SELECT categorie_recherche, count(1) FROM places WHERE wilaya LIKE '%Adrar%' GROUP BY categorie_recherche ORDER BY count(1) DESC")
for r in c.fetchall():
    print(r)

conn.close()

