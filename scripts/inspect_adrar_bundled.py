import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT id, nom, categorie, commune, latitude, longitude, source FROM facilities WHERE wilaya_code = '01'")
current_adrar = c.fetchall()
print(f"Current facilities for Wilaya 01 in bundled DB: {len(current_adrar)}")
for r in current_adrar[:10]:
    print("  ", r)

conn.close()

