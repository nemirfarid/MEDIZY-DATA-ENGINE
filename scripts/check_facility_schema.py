import sqlite3

conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("SELECT id, place_id, nom, adresse, telephone, telephone_raw, latitude, longitude, type_google, wilaya, commune, categorie_recherche FROM places WHERE id = 55876")
print("Sample missing place:", c_sc.fetchone())
conn_sc.close()

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("PRAGMA table_info(facilities)")
for col in c_app.fetchall():
    print(col[1], end=", ")
print()
conn_app.close()

