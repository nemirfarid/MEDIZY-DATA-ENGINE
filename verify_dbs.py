import sqlite3
import hashlib

for db_path in [r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db', r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db']:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('PRAGMA integrity_check')
    integrity = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE wilaya = "Biskra"')
    biskra = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL')
    unique_ids = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE source LIKE "geoalgeria:%"')
    geo_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
    gps_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ""')
    phone_count = c.fetchone()[0]
    
    c.execute('SELECT place_id FROM places WHERE place_id IS NOT NULL AND source NOT LIKE "geoalgeria:%" ORDER BY place_id')
    ids = [r[0] for r in c.fetchall()]
    hash_str = hashlib.sha256(''.join(ids).encode()).hexdigest()[:16]
    
    print('DB: {}'.format(db_path))
    print('  Integrity: {}'.format(integrity))
    print('  Total: {}'.format(total))
    print('  Biskra: {}'.format(biskra))
    print('  GeoAlgeria entries: {}'.format(geo_count))
    print('  Unique place_ids: {}'.format(unique_ids))
    print('  GPS entries: {}'.format(gps_count))
    print('  Phone entries: {}'.format(phone_count))
    print('  place_id hash (excl geoalgeria): {}'.format(hash_str))
    conn.close()