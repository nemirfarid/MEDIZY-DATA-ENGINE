import sqlite3, sys
conn = sqlite3.connect(r'C:/SANTE_DZ_SCRAPER/medizy_scraper.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM places')
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM places WHERE source = 'osm_overpass'")
osm = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM places WHERE source LIKE 'osm_overpass%'")
osm_like = cur.fetchone()[0]
cur.execute('SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL')
distinct = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM places WHERE source LIKE 'osm_overpass:%'")
osm_ids = cur.fetchone()[0]
print('Total:', total)
print('OSM source (exact osm_overpass):', osm)
print('OSM source (like):', osm_like)
print('OSM entries with osm id in place_id:', osm_ids)
print('Distinct place_id:', distinct)
# Show a few OSM entries
cur.execute("SELECT place_id, nom, wilaya, source FROM places WHERE source LIKE 'osm_overpass%' LIMIT 5")
print('--- Sample OSM entries ---')
for r in cur.fetchall():
    sys.stdout.buffer.write((str(r) + "\n").encode("utf-8", errors="replace"))
conn.close()
