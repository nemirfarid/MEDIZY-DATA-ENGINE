import sqlite3

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c_app = conn_app.cursor()
c_app.execute("SELECT count(*) FROM facilities WHERE place_id IS NULL")
print("Facilities with place_id IS NULL:", c_app.fetchone()[0])

c_app.execute("SELECT count(*) FROM facilities WHERE place_id IS NOT NULL")
print("Facilities with place_id IS NOT NULL:", c_app.fetchone()[0])

# Sample facilities with place_id IS NULL
c_app.execute("SELECT id, nom, commune, wilaya, latitude, longitude, source FROM facilities WHERE place_id IS NULL LIMIT 10")
for r in c_app.fetchall():
    print(r)

conn_app.close()

