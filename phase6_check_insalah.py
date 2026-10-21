"""Get correct In Salah GPS coordinates."""
import urllib.request, urllib.parse, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')

query = 'In Salah, Algerie'
url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
    'q': query, 'format': 'json', 'limit': '1', 'addressdetails': '1',
})
req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    time.sleep(1)
    if data:
        lat = data[0]['lat']
        lon = data[0]['lon']
        print(f'In Salah correct GPS: ({lat}, {lon})')
        print(f'Location: {data[0]["display_name"]}')
except Exception as e:
    print(f'Error: {e}')
