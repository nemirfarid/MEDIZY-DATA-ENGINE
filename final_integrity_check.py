import sqlite3

for name, path in [
    ('Production', r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'),
    ('Test', r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db'),
    ('Backup', r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db')
]:
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('PRAGMA integrity_check;')
    integrity = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places;')
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025';")
    miph = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL;')
    unique_ids = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE place_id IS NOT NULL;')
    total_ids = c.fetchone()[0]
    conn.close()
    print(f'{name}: integrity={integrity}, total={total}, MIPH_2025={miph}, place_id_unique={total_ids==unique_ids} ({total_ids}/{unique_ids})')