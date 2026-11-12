import json

with open('scripts/osm_algeria_full.json', 'r', encoding='utf-8') as f:
    osm_data = json.load(f)

print(f"Type of osm_data: {type(osm_data)}, length: {len(osm_data)}")
if isinstance(osm_data, list):
    for el in osm_data:
        tags = el.get('tags', {})
        name = str(tags.get('name', '')) + ' ' + str(tags.get('name:fr', '')) + ' ' + str(tags.get('name:ar', ''))
        if 'tata' in name.lower() or 'bentata' in name.lower():
            print("Found in list:", el)
        lat = el.get('lat') or (el.get('center', {}).get('lat'))
        lon = el.get('lon') or (el.get('center', {}).get('lon'))
        if lat and lon and 36.09 <= lat <= 36.12 and 0.40 <= lon <= 0.43:
            print("OSM in Sidi Ali bounds:", name, tags.get('amenity'), lat, lon)
