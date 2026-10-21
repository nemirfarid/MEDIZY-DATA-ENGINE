"""Search Nominatim for Ait Ouahioune with different queries."""
import urllib.request, urllib.parse, json, time, sys
sys.stdout.reconfigure(encoding='utf-8')

queries = [
    'Ait Ouahioune, Algerie',
    'Ait Ouahioun, Tizi Ouzou, Algerie',
    'Tamanrasset, Algerie',
    'Tizi Ouzou, Algerie',
]

for q in queries:
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': q, 'format': 'json', 'limit': '5', 'addressdetails': '1',
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        time.sleep(1.1)
        if data:
            print(f'Query "{q}": {len(data)} results')
            for i, d in enumerate(data[:3]):
                print(f'  [{i}] {d["display_name"][:80]} -> ({d["lat"]}, {d["lon"]})')
        else:
            print(f'Query "{q}": 0 results')
    except Exception as e:
        print(f'Query "{q}" failed: {e}')
