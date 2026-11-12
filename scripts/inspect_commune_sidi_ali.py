import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()
rows = cur.execute("SELECT id, nom, categorie, commune, wilaya, latitude, longitude FROM facilities WHERE commune = 'Sidi Ali'").fetchall()
print("Total with commune == 'Sidi Ali':", len(rows))
for r in rows[:15]:
    print(r)
print("Distinct wilayas for commune == Sidi Ali:")
print(cur.execute("SELECT DISTINCT wilaya FROM facilities WHERE commune = 'Sidi Ali'").fetchall())

