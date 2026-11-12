import sqlite3

conn_src = sqlite3.connect('medizy_scraper.db')
c_src = conn_src.cursor()

c_src.execute("""
    SELECT count(1) 
    FROM places 
    WHERE wilaya LIKE '%Adrar%' 
      AND latitude IS NOT NULL AND longitude IS NOT NULL 
      AND latitude > 18.0 AND latitude < 38.0
""")
print("Total valid Adrar places in medizy_scraper.db:", c_src.fetchone()[0])

# Sample by category
c_src.execute("""
    SELECT categorie_recherche, count(1) 
    FROM places 
    WHERE wilaya LIKE '%Adrar%' 
    GROUP BY categorie_recherche 
    ORDER BY count(1) DESC
""")
for r in c_src.fetchall():
    print("  ", r)

conn_src.close()

