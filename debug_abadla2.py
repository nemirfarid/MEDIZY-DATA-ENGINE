# Mission 1: Analyser Abadla
import sqlite3

def safe(s):
    if s is None:
        return ''
    return str(s).encode('ascii', 'replace').decode()

TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db'

conn = sqlite3.connect(TEST_DB)
c = conn.cursor()
for pid in ['053be2b97429a342', '90832d666a6d2057']:
    c.execute('SELECT place_id, nom, nom_normalized, wilaya, commune, categorie_recherche, latitude, longitude, source, created_at FROM places WHERE place_id=?', (pid,))
    r = c.fetchone()
    if r:
        print('=== DB:', pid, '===')
        print(f"place_id: {safe(r[0])}")
        print(f"nom: {safe(r[1])}")
        print(f"nom_normalized: {safe(r[2])}")
        print(f"wilaya: {safe(r[3])}")
        print(f"commune: {safe(r[4])}")
        print(f"categorie: {safe(r[5])}")
        print(f"lat: {r[6]}, lng: {r[7]}")
        print(f"source: {safe(r[8])}")
        print(f"created_at: {safe(r[9])}")
    else:
        print('NOT FOUND:', pid)
    print()
conn.close()