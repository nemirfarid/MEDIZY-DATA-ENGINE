import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

non_health = [
    'Salon de coiffure', 'Salle de gym', 'Institut de beaute', 
    'Parfumerie', 'Hammam', 'Barbier', 'Magasin de cosmetiques',
    'Boutique de sante et beaute'
]

for nh in non_health:
    c.execute("DELETE FROM facilities WHERE categorie = ?", (nh,))
    print(f"Deleted {nh}: {c.rowcount} rows")

c.execute("DELETE FROM facilities_rtree")
c.execute("INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon) SELECT id, latitude, latitude, longitude, longitude FROM facilities")
print("Facilities remaining in DB:", c.execute("SELECT count(1) FROM facilities").fetchone()[0])

conn.commit()
conn.close()

