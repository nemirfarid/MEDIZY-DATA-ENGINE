import sqlite3
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Check entries with place_id (using correct column name)
c.execute('SELECT COUNT(*) FROM places WHERE place_id IS NOT NULL AND place_id != ""')
count_pid = c.fetchone()[0]
print(f'With place_id: {count_pid}')

# Check entries with google_maps_url
c.execute('SELECT COUNT(*) FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != ""')
count_url = c.fetchone()[0]
print(f'With google_maps_url: {count_url}')

# Sample entries with URL
c.execute('SELECT id, nom, google_maps_url, horaires FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != "" LIMIT 5')
rows = c.fetchall()
for r in rows:
    print(f'  ID {r[0]}: {r[1][:50]} | URL: {r[2][:80]}... | Horaires: {r[3]}')

conn.close()