import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT id, nom, latitude, longitude, commune, wilaya FROM facilities WHERE id IN (69902, 69907, 69913, 69915)")
for r in c.fetchall():
    print(r)
conn.close()

