import urllib.request
import json
import os

print("Début du téléchargement des 11 143 structures OpenStreetMap Algérie...")

overpass_query = """[out:json][timeout:180];
area["ISO3166-1"="DZ"]->.a;
(
  node["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](area.a);
  way["amenity"~"pharmacy|hospital|clinic|doctors|dentist"](area.a);
);
out center tags;"""

req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=overpass_query.encode('utf-8'),
    headers={'User-Agent': 'MedizyNationalIngest/1.0'}
)

try:
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        elements = data.get('elements', [])
        print(f"Téléchargement réussi : {len(elements)} éléments reçus.")
        os.makedirs('scripts', exist_ok=True)
        with open('scripts/osm_algeria_full.json', 'w', encoding='utf-8') as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)
        print("Sauvegarde effectuée dans scripts/osm_algeria_full.json")
except Exception as e:
    print(f"Erreur téléchargement Overpass : {e}")

