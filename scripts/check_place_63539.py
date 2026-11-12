import sqlite3

conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("SELECT id, place_id, nom, latitude, longitude FROM places WHERE id = 63539 OR place_id = '63539' OR nom LIKE '%زروقي%'")
for r in c_sc.fetchall():
    print("places match:", r)
conn_sc.close()

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT id, nom, commune, wilaya, latitude, longitude, place_id FROM facilities WHERE place_id = '63539'")
for r in c.fetchall():
    print("facility 63539:", r)
conn.close()

