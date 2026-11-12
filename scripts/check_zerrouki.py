import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT id, nom_etablissement_praticien, nom_commune, nom_wilaya, latitude, longitude, coordonnees_gps, source_csv FROM structures WHERE nom_commune = 'Ain Smara' AND nom_etablissement_praticien LIKE '%زروقي%'")
for r in c.fetchall():
    print("structure:", r)

c.execute("SELECT id, nom, commune, wilaya, latitude, longitude, place_id FROM facilities WHERE commune = 'Ain Smara' AND nom LIKE '%زروقي%'")
for r in c.fetchall():
    print("facility:", r)

# Also check Dr Ainouch in structures
c.execute("SELECT id, nom_etablissement_praticien, nom_commune, nom_wilaya, latitude, longitude, coordonnees_gps, source_csv FROM structures WHERE nom_etablissement_praticien LIKE '%Ainouch%' or nom_etablissement_praticien LIKE '%عاينوش%'")
for r in c.fetchall():
    print("Ainouch in structures:", r)

conn.close()

