import sqlite3

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT id, place_id, nom, latitude, longitude FROM facilities WHERE nom = 'Centre Anti Cancer (CAC) ADRAR'")
print("CAC Adrar facility:", c_app.fetchall())

c_app.execute("SELECT id, place_id, nom, latitude, longitude FROM facilities WHERE nom = 'Cabinet Dr Senoussi A Née Alliane'")
print("Senoussi facility:", c_app.fetchall())

conn_app.close()

