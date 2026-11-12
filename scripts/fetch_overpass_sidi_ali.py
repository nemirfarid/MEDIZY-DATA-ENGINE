import urllib.request
import json

url = 'https://overpass-api.de/api/interpreter'
query = """[out:json][timeout:25];
(
  node["amenity"~"pharmacy|doctors|clinic|hospital|dentist"](36.08,0.40,36.12,0.44);
  way["amenity"~"pharmacy|doctors|clinic|hospital|dentist"](36.08,0.40,36.12,0.44);
);
out center;"""

try:
    req = urllib.request.Request(url, data=query.encode('utf-8'))
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode('utf-8'))
    print(f"Total OSM elements in Sidi Ali urban bounds: {len(data.get('elements', []))}")
    for el in data.get('elements', []):
        tags = el.get('tags', {})
        lat = el.get('lat') or el.get('center', {}).get('lat')
        lon = el.get('lon') or el.get('center', {}).get('lon')
        print(f"  {tags.get('name', 'Sans nom')} | {tags.get('amenity')} | ({lat}, {lon})")
except Exception as e:
    print("Error fetching:", e)

