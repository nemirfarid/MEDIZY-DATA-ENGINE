import json

with open(r'assets\data\medizy_wilayas_index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Number of wilayas in index:', len(data['wilayas']))
for w in sorted(data['wilayas'], key=lambda x: int(x['code'])):
    bb = w['bounding_box']
    c_lat = (bb['min_lat'] + bb['max_lat']) / 2
    c_lon = (bb['min_lon'] + bb['max_lon']) / 2
    print(f"{w['code']}: {w['name']} ({w['total_facilities']} fiches) -> [{c_lat:.4f}, {c_lon:.4f}]")
