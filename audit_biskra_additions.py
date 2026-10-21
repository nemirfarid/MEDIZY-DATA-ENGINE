import sqlite3

# Detailed audit of the 6 Biskra additions
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db')
c = conn.cursor()

# Get the 6 GeoAlgeria entries
c.execute('''
    SELECT id, place_id, nom, wilaya, commune, categorie_recherche, 
           latitude, longitude, source, created_at
    FROM places 
    WHERE source LIKE "geoalgeria:%"
    ORDER BY id
''')
geo_rows = c.fetchall()

print("=" * 80)
print("AUDIT DES 6 AJOUTS GEOALGERIA BISKRA (medizy_scraper_test.db)")
print("=" * 80)

def safe(s):
    if s is None:
        return 'NULL'
    return str(s).encode('ascii', 'replace').decode()

for row in geo_rows:
    id_, place_id, nom, wilaya, commune, cat, lat, lng, source, created = row
    print("\n--- Entree #{}: {} ---".format(id_, place_id))
    print("  Nom officiel: {}".format(safe(nom)))
    print("  Type/Category: {}".format(safe(cat)))
    print("  Wilaya: {} | Commune: {}".format(safe(wilaya), safe(commune)))
    print("  GPS: ({}, {})".format(lat, lng))
    print("  Source: {}".format(safe(source)))
    print("  Date creation: {}".format(safe(created)))
    print("  place_id: {}".format(safe(place_id)))

    # Check for corresponding existing establishment
    c.execute('''
        SELECT id, nom, commune, categorie_recherche, latitude, longitude, source
        FROM places 
        WHERE wilaya = ? AND id != ? AND source NOT LIKE "geoalgeria:%"
        ORDER BY 
            ABS(latitude - ?) + ABS(longitude - ?) ASC
        LIMIT 3
    ''', (wilaya, id_, lat, lng))
    nearby = c.fetchall()
    print("  Etablissements proches (non-GeoAlgeria):")
    for n in nearby:
        n_id, n_nom, n_commune, n_cat, n_lat, n_lng, n_source = n
        dist = ((n_lat - lat)**2 + (n_lng - lng))**0.5 if n_lat and n_lng else None
        print("    id={} | {} | {} | {} | GPS=({}, {}) | dist={} | {}".format(
            n_id, safe(n_nom), safe(n_commune), safe(n_cat), n_lat, n_lng, 
            "{:.4f}".format(dist) if dist else 'N/A', safe(n_source)))

conn.close()