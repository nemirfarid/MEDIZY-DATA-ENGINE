import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT id, nom, categorie, latitude, longitude, commune, wilaya FROM facilities WHERE nom LIKE '%Ben%Tata%' OR nom LIKE '%Bentata%' OR nom LIKE '%بن%تات%'")
rows = c.fetchall()
print(f"Dr Ben Tata in facilities ({len(rows)} found):")
for r in rows:
    print(r)

# Check Mostaganem facilities around CW 42 or Si Afif or Rue de la Palestine
c.execute("SELECT id, nom, categorie, latitude, longitude, adresse FROM facilities WHERE wilaya_code = '27' AND (adresse LIKE '%Palestine%' OR nom LIKE '%Palestine%' OR adresse LIKE '%Afif%' OR nom LIKE '%Afif%')")
print("Facilities near Palestine/Afif:")
for r in c.fetchall():
    print(r)

conn.close()
