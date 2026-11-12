import urllib.request
import json

overpass_query = """[out:json][timeout:90];
area["ISO3166-1"="DZ"]->.a;
(
  node["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](area.a);
  way["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](area.a);
);
out count;"""

req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=overpass_query.encode('utf-8'),
    headers={'User-Agent': 'MedizyInspector/1.0'}
)

try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        elements = data.get('elements', [])
        print("Résultat décompte OpenStreetMap Algérie :", elements)
except Exception as e:
    print(f"Erreur Overpass: {e}")

