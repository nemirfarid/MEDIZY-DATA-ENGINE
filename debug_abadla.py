# Mission 1: Analyser Abadla
import sqlite3
import csv

TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db'
GEO_CSV = r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv'

# Check entries in test DB
conn = sqlite3.connect(TEST_DB)
c = conn.cursor()
for pid in ['053be2b97429a342', '90832d666a6d2057']:
    c.execute('SELECT place_id, nom, nom_normalized, wilaya, commune, categorie_recherche, latitude, longitude, source, created_at FROM places WHERE place_id=?', (pid,))
    r = c.fetchone()
    if r:
        print('=== DB:', pid, '===')
        print(r)
    else:
        print('NOT FOUND:', pid)
conn.close()