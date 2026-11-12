import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()

c.execute("SELECT id, wilaya_code, nom_fr, nom_ar, latitude, longitude FROM communes WHERE wilaya_code = '01'")
adrar_communes = c.fetchall()
print(f"Official Communes for Wilaya 01 (Adrar): {len(adrar_communes)}")
for com in adrar_communes:
    print(f"  {com[0]}. Code: {com[1]} | {com[2]} ({com[3]}) at ({com[4]}, {com[5]})")

# Check places already scraped in medizy_scraper.db for Adrar
c.execute("SELECT count(1) FROM places WHERE wilaya LIKE '%Adrar%' OR wilaya_normalized LIKE '%adrar%'")
print(f"\nPlaces in medizy_scraper.db for Adrar: {c.fetchone()[0]}")

conn.close()

