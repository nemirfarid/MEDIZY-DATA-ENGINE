import os
import sqlite3

# File sizes
prod_size = os.path.getsize(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
backup_size = os.path.getsize(r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db')
print('Production size: {} bytes ({:.2f} MB)'.format(prod_size, prod_size/1024/1024))
print('Backup size:     {} bytes ({:.2f} MB)'.format(backup_size, backup_size/1024/1024))

# Integrity checks
for name, path in [('Production', r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'),
                   ('Backup', r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db')]:
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('PRAGMA integrity_check')
    integrity = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL')
    unique_ids = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM places WHERE source LIKE 'geoalgeria:%'")
    geo_count = c.fetchone()[0]
    conn.close()
    print('{}: integrity={}, total={}, unique_ids={}, geoalgeria={}'.format(name, integrity, total, unique_ids, geo_count))