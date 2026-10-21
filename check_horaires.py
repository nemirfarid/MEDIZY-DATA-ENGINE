import sqlite3
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Count entries without horaires
c.execute('SELECT COUNT(*) FROM places WHERE horaires IS NULL OR horaires = ""')
count = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM places')
total = c.fetchone()[0]
print(f'Total: {total}, Without horaires: {count}, With horaires: {total - count}')

# Check entries with google_maps_url but no horaires
c.execute('SELECT COUNT(*) FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != "" AND (horaires IS NULL OR horaires = "")')
count_with_url = c.fetchone()[0]
print(f'With URL but no horaires: {count_with_url}')

# Check entries with place_id
c.execute('SELECT COUNT(*) FROM places WHERE place_id_si_visible IS NOT NULL AND place_id_si_visible != ""')
count_pid = c.fetchone()[0]
print(f'With place_id: {count_pid}')

conn.close()