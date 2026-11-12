import json
import sqlite3

# Load OSM National
with open('scripts/osm_algeria_full.json', 'r', encoding='utf-8') as f:
    osm_elements = json.load(f)

# Bounding box of Adrar municipality urban center
# Centered around (27.8742, -0.2939) within radius ~10km (27.80 to 27.93, -0.35 to -0.24)
adrar_center_osm = []
for el in osm_elements:
    lat = el.get('lat') or (el.get('center', {}).get('lat'))
    lon = el.get('lon') or (el.get('center', {}).get('lon'))
    if lat and lon and 27.82 <= lat <= 27.92 and -0.34 <= lon <= -0.24:
        tags = el.get('tags', {})
        name = tags.get('name') or tags.get('name:fr') or tags.get('name:ar')
        amenity = tags.get('amenity', '')
        adrar_center_osm.append({
            'id': el.get('id'),
            'name': name,
            'amenity': amenity,
            'lat': lat,
            'lon': lon,
            'tags': tags
        })

print(f"OSM structures in Adrar Chef-lieu: {len(adrar_center_osm)}")
for s in adrar_center_osm:
    print(f"  {s['name']} | {s['amenity']} | ({s['lat']}, {s['lon']})")

# Also check Google Maps CSV for Adrar
import pandas as pd
df = pd.read_csv('C:/Users/pc lenovo/Downloads/Google Maps Extractor/all-task-1-overview.csv', low_memory=False)
gmaps_adrar = df[df['address'].str.contains('Adrar', case=False, na=False) | df['name'].str.contains('Adrar', case=False, na=False)]
print(f"\nGoogle Maps Extractor matches containing 'Adrar': {len(gmaps_adrar)}")
for i, r in gmaps_adrar.iterrows():
    print(f"  {r['name']} | {r['main_category']} | {r['address']} | {r['link']}")

