import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# 1. Update 15414 to authentic OSM Dr Ben Tata Pédiatre in Sidi Ali
c.execute("""
    UPDATE facilities
    SET nom = 'Pédiatre Dr Ben Tata',
        categorie = 'Pediatre',
        wilaya = 'Mostaganem',
        wilaya_code = '27',
        commune = 'Sidi Ali',
        adresse = 'CW 42, Sidi Ali, Mostaganem',
        latitude = 36.1012142,
        longitude = 0.4144845,
        source = 'OpenStreetMap Verified'
    WHERE id = 15414
""")
print(f"Updated record 15414: {c.rowcount}")

# 2. Re-insert Dr Tilmatine Bentata Amel with her genuine Google Maps coordinates in Mostaganem
c.execute("""
    INSERT INTO facilities (place_id, nom, categorie, wilaya, wilaya_code, commune, adresse, latitude, longitude, source)
    VALUES (
        'ChIJ7ZIIqkQDghIRBv8Uz2rMbMk',
        'Cabinet De Gynecologie Obstetrique Dr Tilmatine Bentata Amel',
        'Gynecologue-obstetricien',
        'Mostaganem',
        '27',
        'Mostaganem',
        'Mostaganem, Algérie',
        35.9197902,
        0.1031769,
        'Google Maps Extractor'
    )
""")
print(f"Inserted Dr Tilmatine Bentata Amel: {c.rowcount}")

conn.commit()

# Rebuild spatial index
c.execute("DELETE FROM facilities_rtree")
c.execute("INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon) SELECT id, latitude, latitude, longitude, longitude FROM facilities")
conn.commit()

c.execute("SELECT id, nom, categorie, latitude, longitude, commune FROM facilities WHERE nom LIKE '%bentata%' OR nom LIKE '%ben tata%'")
for r in c.fetchall():
    print("Verification:", r)

conn.close()

