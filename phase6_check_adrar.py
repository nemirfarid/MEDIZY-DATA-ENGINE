"""Get correct Adrar GPS coordinates."""
import urllib.request, urllib.parse, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')

query = 'Adrar, Algerie'
url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
    'q': query, 'format': 'json', 'limit': '5', 'addressdetails': '1',
})
req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    time.sleep(1)
    if data:
        for i, d in enumerate(data[:3]):
            print(f'  [{i}] ({d["lat"]}, {d["lon"]}) - {d["display_name"][:100]}')
except Exception as e:
    print(f'Error: {e}')
