import urllib.request
import json

overpass_query = """[out:json][timeout:60];
(
  node["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](35.7,0.0,36.4,0.6);
  way["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](35.7,0.0,36.4,0.6);
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
        print(f"Trouve {len(elements)} structures OSM dans la wilaya de Mostaganem.")
        named = [el for el in elements if 'name' in el.get('tags', {}) or 'name:fr' in el.get('tags', {}) or 'name:ar' in el.get('tags', {})]
        print(f"Dont {len(named)} structures nommees.")
        with open('scripts/osm_mostaganem.json', 'w', encoding='utf-8') as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"Erreur: {e}")

