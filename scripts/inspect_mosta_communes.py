import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()
rows = cur.execute("SELECT id, nom, wilaya, commune, latitude, longitude FROM facilities WHERE wilaya LIKE '%Mostaganem%'").fetchall()
print("Total in Mostaganem:", len(rows))
communes = {}
for r in rows:
    com = r[3]
    communes[com] = communes.get(com, 0) + 1

print("Communes distribution in Mostaganem:")
for com, count in sorted(communes.items(), key=lambda x: x[1], reverse=True)[:15]:
    sample = cur.execute(f"SELECT latitude, longitude FROM facilities WHERE wilaya LIKE '%Mostaganem%' AND commune = ? LIMIT 1", (com,)).fetchone()
    print(f"  {com}: {count} structures -> lat: {sample[0]}, lon: {sample[1]}")

