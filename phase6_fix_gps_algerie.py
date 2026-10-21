"""Fix GPS entries outside Algeria that are clearly geocoded to wrong countries."""
import sqlite3, urllib.request, urllib.parse, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Entries with GPS clearly outside Algeria (France, South Africa, etc.)
# Borderline entries (Adrar -9.51, In Salah 10.17) are kept as legitimate border areas
CLEARLY_WRONG = [
    # (id, name, wilaya)
    (67579, 'Dr Imed Ben Salah', 'In Salah'),       # Lat 36.87, Lon 10.17 (Libya/Tunisia border - borderline)
    (69865, 'Orthophoniste Mila', 'Mila'),            # Lat 45.40, Lon 4.36 (Lyon, France!)
    (70776, 'عيادة طبية جراحية', 'Naâma'),             # Lat 41.21, Lon 0.18 (Perpignan, France!)
    (77878, 'ORL Dr Yassine BALHI', 'Tizi Ouzou'),    # Lat 30.70, Lon -26.43 (Cape Town, South Africa!)
]

# Actually, looking again: Adrar (30.39,-9.51) is at the Morocco border
# and In Salah (36.87, 10.17) is at the Libya/Tunisia border
# Those are borderline. The 3 clearly wrong ones are Mila (France), Naâma (France), Tizi Ouzou (South Africa)

CLEARLY_WRONG = [
    (69865, 'Orthophoniste Mila', 'Mila'),
    (70776, 'عيادة طبية جراحية', 'Naâma'),
    (77878, 'ORL Dr Yassine BALHI', 'Tizi Ouzou'),
]

for entry_id, name, wilaya in CLEARLY_WRONG:
    # Get current values
    c.execute('SELECT latitude, longitude FROM places WHERE id = ?', (entry_id,))
    cur_lat, cur_lon = c.fetchone()
    print(f'Fixing: {name} ({wilaya}) - current GPS: ({cur_lat}, {cur_lon})')

    # Geocode using wilaya name
    query = f'{wilaya}, Algerie'
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': query, 'format': 'json', 'limit': '1', 'addressdetails': '1',
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        time.sleep(1.2)
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            addr = data[0].get('address', {})
            commune = addr.get('town') or addr.get('village') or addr.get('city') or wilaya
            print(f'  New GPS: ({lat:.4f}, {lon:.4f}), commune: {commune}')
            c.execute(
                'UPDATE places SET latitude = ?, longitude = ?, commune = ?, commune_source = ?, commune_confidence = ?, commune_updated_at = ? WHERE id = ?',
                (lat, lon, commune, 'Nominatim_correction', 0.5, '2026-10-10 20:35:00', entry_id))
            conn.commit()
    except Exception as e:
        print(f'  Error: {e}')

# Final check
c.execute('''
    SELECT id, nom, wilaya, latitude, longitude 
    FROM places 
    WHERE latitude < 19.0 OR latitude > 37.5 OR longitude < -9.0 OR longitude > 10.0
''')
remaining = c.fetchall()
print(f'\nRemaining entries outside Algeria bounds: {len(remaining)}')
for r in remaining:
    print(f'  {r}')

c.execute('SELECT COUNT(*), COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) FROM places')
total, with_gps = c.fetchone()
print(f'Total: {total}, With GPS: {with_gps}')
conn.close()
