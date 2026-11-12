import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT id, nom, categorie, commune, latitude, longitude, source FROM facilities WHERE wilaya_code = '01'")
rows = c.fetchall()
print(f"Total current facilities for Wilaya 01 (Adrar): {len(rows)}")
for r in rows:
    print("  ", r)

conn.close()

