"""Fix GPS for the remaining entries (Ait Ouahioune, Mila)."""
import sqlite3, urllib.request, urllib.parse, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Check Mila entry
c.execute('SELECT id, nom, latitude, longitude FROM places WHERE id = 80912')
print(f'Mila entry: {c.fetchone()}')

# Check Ait Ouahioune entry
c.execute('SELECT id, nom, latitude, longitude FROM places WHERE id = 77898')
print(f'Ait Ouahioune entry: {c.fetchone()}')

# Geocode Ait Ouahioune, Tizi Ouzou, Algerie
query = 'Ait Ouahioune, Tizi Ouzou, Algerie'
url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
    'q': query, 'format': 'json', 'limit': '5', 'addressdetails': '1',
})
req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    time.sleep(1)
    print(f'Nominatim results for Ait Ouahioune: {len(data)}')

    if data:
        lat = float(data[0]['lat'])
        lon = float(data[0]['lon'])
        addr = data[0].get('address', {})
        commune = addr.get('town') or addr.get('village') or addr.get('city') or 'Ait Ouahioune'
        print(f'Geocoded Ait Ouahioune -> ({lat:.4f}, {lon:.4f}), commune: {commune}')
        c.execute(
            'UPDATE places SET latitude = ?, longitude = ?, commune = ?, commune_source = ?, commune_confidence = ?, commune_updated_at = ? WHERE id = 77898',
            (lat, lon, commune, 'Nominatim', 0.7, '2026-10-10 20:31:00'))
        conn.commit()
except Exception as e:
    print(f'Error geocoding Ait Ouahioune: {e}')

# If Mila wasn't updated, fix it
c.execute('SELECT latitude, longitude FROM places WHERE id = 80912')
row = c.fetchone()
if row[0] is None or row[1] is None:
    print('Mila GPS still missing — re-geocoding...')
    query = 'Mila, Algerie'
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': query, 'format': 'json', 'limit': '1', 'addressdetails': '1',
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        time.sleep(1)
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            print(f'Geocoded Mila -> ({lat:.4f}, {lon:.4f})')
            c.execute(
                'UPDATE places SET latitude = ?, longitude = ?, commune = ?, commune_source = ?, commune_confidence = ?, commune_updated_at = ? WHERE id = 80912',
                (lat, lon, 'Mila', 'Nominatim', 0.8, '2026-10-10 20:31:00'))
            conn.commit()
    except Exception as e:
        print(f'Error geocoding Mila: {e}')

c.execute('SELECT COUNT(*), COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) FROM places')
total, with_gps = c.fetchone()
print(f'\nFinal: Total={total}, With GPS={with_gps}, Missing GPS={total - with_gps}')

# Verify entries without GPS
c.execute('SELECT id, nom FROM places WHERE latitude IS NULL OR longitude IS NULL')
for r in c.fetchall():
    print(f'  Still missing GPS: {r}')
conn.close()
