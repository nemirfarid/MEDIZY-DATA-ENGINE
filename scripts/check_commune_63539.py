import sqlite3

conn_sc = sqlite3.connect('medizy_scraper.db')
c_sc = conn_sc.cursor()
c_sc.execute("SELECT id, place_id, nom, latitude, longitude, commune_id FROM places WHERE id = 63539")
place_row = c_sc.fetchone()
print("Place 63539:", place_row)

c_sc.execute("SELECT id, nom_fr, nom_ar, latitude, longitude FROM communes WHERE id = ?", (place_row[5],))
commune_row = c_sc.fetchone()
print("Commune in scraper:", commune_row)

conn_sc.close()

