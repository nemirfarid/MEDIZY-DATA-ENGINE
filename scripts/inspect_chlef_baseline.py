import sqlite3

conn_scraper = sqlite3.connect('medizy_scraper.db')
c_s = conn_scraper.cursor()

c_s.execute("SELECT id, nom_fr, nom_ar, latitude, longitude FROM communes WHERE wilaya_code = '02' ORDER BY nom_fr")
communes_chlef = c_s.fetchall()
print(f"Total official communes for Wilaya 02 (Chlef): {len(communes_chlef)}")
for com in communes_chlef:
    print(f"  * {com[1]} ({com[2]}) -> Coords: ({com[3]}, {com[4]})")

# Check places already available in medizy_scraper.db for Chlef
c_s.execute("SELECT count(1) FROM places WHERE wilaya LIKE '%Chlef%' OR wilaya_normalized LIKE '%chlef%'")
print(f"\nTotal health places available in medizy_scraper.db for Chlef: {c_s.fetchone()[0]}")

# Check breakdown by category
c_s.execute("""
    SELECT categorie_recherche, count(1) 
    FROM places 
    WHERE wilaya LIKE '%Chlef%' OR wilaya_normalized LIKE '%chlef%'
    GROUP BY categorie_recherche 
    ORDER BY count(1) DESC
""")
for r in c_s.fetchall():
    print("  -", r)

conn_scraper.close()

