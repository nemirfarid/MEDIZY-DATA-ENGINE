import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()

print("Sample 10 Alger structures:")
rows = cur.execute("SELECT id, nom, wilaya, commune, latitude, longitude, source FROM facilities WHERE wilaya = 'Alger' LIMIT 10").fetchall()
for r in rows:
    print(" ", r)

print("\nSample 10 Oran structures:")
rows = cur.execute("SELECT id, nom, wilaya, commune, latitude, longitude, source FROM facilities WHERE wilaya = 'Oran' LIMIT 10").fetchall()
for r in rows:
    print(" ", r)

