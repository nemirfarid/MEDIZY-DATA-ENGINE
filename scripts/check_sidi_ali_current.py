import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT id, nom, categorie, wilaya, commune, latitude, longitude, telephone FROM facilities WHERE nom LIKE '%Ainouch%' OR nom LIKE '%عاينوش%'")
print("Ainouch in current bundled DB:", c.fetchall())

c.execute("SELECT id, nom, categorie, wilaya, commune, latitude, longitude, telephone FROM facilities WHERE nom LIKE '%Boussaid%'")
print("Boussaid in current bundled DB:", c.fetchall())

c.execute("SELECT id, nom, categorie, wilaya, commune, latitude, longitude, telephone FROM facilities WHERE nom LIKE '%Ouzani%' OR nom LIKE '%وزاني%'")
print("Ouzani in current bundled DB:", c.fetchall())

c.execute("SELECT id, nom, categorie, wilaya, commune, latitude, longitude, telephone FROM facilities WHERE commune = 'Sidi Ali'")
rows = c.fetchall()
print(f"Total in Sidi Ali: {len(rows)}")
for r in rows[:10]:
    print(" ", r)

conn.close()

