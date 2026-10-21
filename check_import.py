import sqlite3
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db')
c = conn.cursor()

# Check the business duplicate matches
for dup_id in [80913, 80918]:
    c.execute('SELECT id, nom, wilaya, commune, categorie_recherche, source FROM places WHERE id = ?', (dup_id,))
    r = c.fetchone()
    if r:
        nom = r[1].encode('ascii', 'replace').decode()
        print('DB id={}: {} | {} | {} | {} | {}'.format(r[0], nom, r[2], r[3], r[4], r[5]))

# Check newly imported GeoAlgeria entries
c.execute('SELECT id, place_id, nom, wilaya, commune, categorie_recherche, latitude, longitude, source FROM places WHERE source LIKE "geoalgeria:%"')
rows = c.fetchall()
print('\nNew GeoAlgeria entries:')
for r in rows:
    nom = r[2].encode('ascii', 'replace').decode()
    print('  id={} place_id={} | {} | {} | {} | {} | GPS=({}, {})'.format(
        r[0], r[1], nom, r[3], r[4], r[5], r[6], r[7]))

conn.close()