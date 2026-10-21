import sqlite3

dbs = [
    (r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db', 'Production'),
    (r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db', 'Backup Audit'),
    (r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db', 'Test (Biskra)'),
    (r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db', 'National Test'),
    (r'C:\SANTE_DZ_SCRAPER\medizy_scraper_synthetic.db', 'Synthetic'),
]

for path, name in dbs:
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('PRAGMA integrity_check')
    integrity = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL')
    unique_ids = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM places WHERE source LIKE 'geoalgeria:%'")
    geo = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE wilaya = "Biskra"')
    biskra = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
    gps = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ""')
    phone = c.fetchone()[0]
    conn.close()
    print('{}: integrity={}, total={}, unique_ids={}, geoalgeria={}, biskra={}, gps={}, phone={}'.format(
        name, integrity, total, unique_ids, geo, biskra, gps, phone))