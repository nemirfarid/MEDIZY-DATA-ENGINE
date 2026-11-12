import sqlite3

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT nom, telephone, latitude, longitude, commune, wilaya FROM facilities WHERE nom LIKE '%Senoussi%' OR telephone LIKE '%0657 55 83 27%'")
print("Senoussi search:", c_app.fetchall())

c_app.execute("SELECT nom, telephone, latitude, longitude, commune, wilaya FROM facilities WHERE nom LIKE '%Centre Anti Cancer (CAC) ADRAR%'")
print("CAC Adrar search:", c_app.fetchall())

conn_app.close()

