import json

with open('scripts/osm_algeria_full.json', 'r', encoding='utf-8') as f:
    elements = json.load(f)

print(f"Total elements in osm_algeria_full.json: {len(elements)}")

# Filter elements in Sidi Ali urban area: 36.08 to 36.12 lat, 0.40 to 0.43 lon
sidi_ali_osm = []
for el in elements:
    lat = el.get('lat') or (el.get('center', {}).get('lat'))
    lon = el.get('lon') or (el.get('center', {}).get('lon'))
    if lat and lon and 36.09 <= lat <= 36.115 and 0.40 <= lon <= 0.435:
        tags = el.get('tags', {})
        name = tags.get('name') or tags.get('name:fr') or tags.get('name:ar') or 'Sans nom'
        amenity = tags.get('amenity', '')
        sidi_ali_osm.append((el.get('id'), name, amenity, lat, lon, tags))

print(f"Elements in Sidi Ali urban zone: {len(sidi_ali_osm)}")
for item in sidi_ali_osm:
    print(f"  ID {item[0]}: {item[1]} [{item[2]}] at ({item[3]}, {item[4]})")

