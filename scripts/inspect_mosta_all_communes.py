import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()
rows = cur.execute("SELECT count(*), min(latitude), max(latitude), min(longitude), max(longitude) FROM facilities WHERE wilaya_code = '27'").fetchall()
print("Wilaya 27 (Mostaganem) in facilities:", rows)

communes = cur.execute("SELECT commune, count(*), avg(latitude), avg(longitude) FROM facilities WHERE wilaya_code = '27' GROUP BY commune ORDER BY count(*) DESC").fetchall()
print(f"Total communes in Mostaganem in facilities: {len(communes)}")
for c in communes:
    print(f"  {c[0]}: {c[1]} structures -> ({round(c[2], 4)}, {round(c[3], 4)})")

