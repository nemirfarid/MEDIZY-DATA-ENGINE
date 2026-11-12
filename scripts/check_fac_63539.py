import sqlite3

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT id, nom, commune, wilaya, latitude, longitude, place_id FROM facilities WHERE place_id = '63539'")
print("Facility:", c_app.fetchone())
conn_app.close()

