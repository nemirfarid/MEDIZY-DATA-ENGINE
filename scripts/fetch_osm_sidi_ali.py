import urllib.request
import json

overpass_query = """[out:json][timeout:25];
(
  node["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](36.08,0.40,36.13,0.43);
  way["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](36.08,0.40,36.13,0.43);
);
out center;"""

req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=overpass_query.encode('utf-8'),
    headers={'User-Agent': 'MedizyInspector/1.0'}
)

try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        elements = data.get('elements', [])
        print(f"Trouvé {len(elements)} structures de santé OSM à Sidi Ali :")
        for el in elements:
            tags = el.get('tags', {})
            name = tags.get('name', tags.get('name:fr', tags.get('name:ar', 'Sans nom')))
            lat = el.get('lat') or el.get('center', {}).get('lat')
            lon = el.get('lon') or el.get('center', {}).get('lon')
            amenity = tags.get('amenity')
            print(f"- {name} | Type: {amenity} | Coordonnées exactes: lat={lat}, lon={lon}")
except Exception as e:
    print(f"Erreur Overpass: {e}")

