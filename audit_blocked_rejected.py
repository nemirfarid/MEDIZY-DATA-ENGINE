import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db')
c = conn.cursor()

def safe(s):
    if s is None:
        return 'NULL'
    return str(s).encode('ascii', 'replace').decode()

print("=" * 80)
print("AUDIT DES 5 DOUBLONS METIER BLOQUES")
print("=" * 80)

for dup_id in [80913, 80918]:
    c.execute('''
        SELECT id, place_id, nom, wilaya, commune, categorie_recherche, 
               latitude, longitude, source, created_at
        FROM places WHERE id = ?
    ''', (dup_id,))
    row = c.fetchone()
    if row:
        id_, place_id, nom, wilaya, commune, cat, lat, lng, source, created = row
        print("\n--- Doublon existant id={} ---".format(id_))
        print("  Nom: {}".format(safe(nom)))
        print("  Type: {} | Wilaya: {} | Commune: {}".format(safe(cat), wilaya, safe(commune)))
        print("  GPS: ({}, {})".format(lat, lng))
        print("  Source: {}".format(safe(source)))
        print("  place_id: {}".format(safe(place_id)))
        print("  Date creation: {}".format(safe(created)))

print("\n" + "=" * 80)
print("LES 5 CANDIDATS GEOALGERIA BLOQUES COMME DOUBLONS METIER")
print("=" * 80)

blocked = [
    ('07-ehs-02', 'Etablissement Hospitalier Specialise Mchouneche', 'hopital specialise', 'Biskra', "M'Chouneche", 34.949896, 5.984274, 'matched to 80913'),
    ('07-ehs-03', 'Etablissement Hospitalier Specialise Mere en Enfant Biskra', 'hopital specialise', 'Biskra', 'Biskra', 34.849784, 5.742165, 'matched to 80913'),
    ('07-epsp-04', 'Etablissement Public de Sante de Proximite Sidi Okba', 'centre de sante', 'Biskra', 'Sidi Okba', 34.74512, 5.9, 'matched to 80918'),
    ('07-epsp-05', 'Etablissement Public de Sante de Proximite Tolga', 'centre de sante', 'Biskra', 'Tolga', 34.7214, 5.380213, 'matched to 80918'),
    ('07-epsp-06', 'Etablissement Public de Sante de Proximite Zribet El Oued', 'centre de sante', 'Biskra', 'Zeribet El Oued', 34.683, 6.511, 'matched to 80918'),
]

for geo_id, nom, cat, wilaya, commune, lat, lng, match in blocked:
    print("\n--- {} ---".format(geo_id))
    print("  Nom: {}".format(safe(nom)))
    print("  Type: {} | Wilaya: {} | Commune: {}".format(safe(cat), wilaya, safe(commune)))
    print("  GPS: ({}, {})".format(lat, lng))
    print("  Bloque car: {}".format(match))

print("\n" + "=" * 80)
print("AUDIT DES 3 REJETS (PAS DE GPS)")
print("=" * 80)

rejected = [
    ('07-eph-05', 'المؤسسة الاستشفائية المتخصصة في طب وجراحة العيون، الطب، طب و جراحة الأطف', 'hopital public', 'Biskra', '', None, None),
    ('07-epsp-02', 'Etablissement Public de Sante de Proximite Djemorah', 'centre de sante', 'Biskra', '', None, None),
    ('07-epsp-03', 'Etablissement Public de Sante de Proximite El Kantara', 'centre de sante', 'Biskra', '', None, None),
]

for geo_id, nom, cat, wilaya, commune, lat, lng in rejected:
    print("\n--- {} ---".format(geo_id))
    print("  Nom: {}".format(safe(nom)))
    print("  Type: {} | Wilaya: {} | Commune: {}".format(safe(cat), wilaya, safe(commune)))
    print("  GPS: ({}, {})".format(lat, lng))
    print("  Raision: Pas de coordonnees GPS dans la source GeoAlgeria")

# Verify no incorrect merges - check that the 6 imported are distinct
print("\n" + "=" * 80)
print("VERIFICATION: AUCUNE FUSION INCORRECTE DES 6 IMPORTES")
print("=" * 80)
c.execute('''
    SELECT id, place_id, nom, wilaya, commune, categorie_recherche, latitude, longitude
    FROM places WHERE source LIKE "geoalgeria:%" ORDER BY id
''')
rows = c.fetchall()
place_ids = set()
for r in rows:
    place_ids.add(r[1])
    print("  id={} place_id={} | {} | {} | {} | GPS=({}, {})".format(
        r[0], r[1], safe(r[2]), r[3], safe(r[4]), r[5], r[6], r[7]))
print("\nNombre de place_id uniques: {} (attendu: 6)".format(len(place_ids)))

# Verify Biskra count
c.execute('SELECT COUNT(*) FROM places WHERE wilaya = "Biskra"')
biskra_total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM places WHERE wilaya = "Biskra" AND source LIKE "geoalgeria:%"')
geo_count = c.fetchone()[0]
print("\nTotal Biskra dans test DB: {} (etait 141, +{})".format(biskra_total, geo_count))

# Categories
c.execute('SELECT DISTINCT categorie_recherche, COUNT(*) FROM places WHERE wilaya = "Biskra" GROUP BY categorie_recherche ORDER BY COUNT(*) DESC')
cats = c.fetchall()
print("\nCategories Biskra:")
for cat, count in cats:
    print("  {}: {}".format(safe(cat), count))

# Communes
c.execute('SELECT DISTINCT commune, COUNT(*) FROM places WHERE wilaya = "Biskra" AND commune IS NOT NULL AND commune != "" GROUP BY commune ORDER BY COUNT(*) DESC')
communes = c.fetchall()
print("\nCommunes Biskra ({} total):".format(len(communes)))
for comm, count in communes:
    print("  {}: {}".format(safe(comm), count))

conn.close()