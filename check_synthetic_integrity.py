import sqlite3

for name, path in [
    ('Synthetic', r'C:\SANTE_DZ_SCRAPER\medizy_scraper_synthetic.db'),
]:
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('PRAGMA integrity_check;')
    integrity = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places;')
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025_SYNTH';")
    synth = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL;')
    unique_ids = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE place_id IS NOT NULL;')
    total_ids = c.fetchone()[0]
    conn.close()
    print(f'{name}: integrity={integrity}, total={total}, MIPH_2025_SYNTH={synth}, place_id_unique={total_ids==unique_ids} ({total_ids}/{unique_ids})')