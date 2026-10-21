#!/usr/bin/env python3
"""Phase 3 - Analyse des couvertures par wilaya et catégorie pour identifier les déficits."""
import csv, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

csv_path = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Deduplicate by google_maps_url
url_seen = {}
unique_rows = []
for r in rows:
    url = r.get('google_maps_url', '').strip()
    if url and url not in url_seen:
        url_seen[url] = True
        unique_rows.append(r)
    elif not url:
        # Keep rows without URL (rare)
        unique_rows.append(r)

print(f"Total CSV rows: {len(rows)}")
print(f"Unique by URL: {len(url_seen)}")
print(f"Rows without URL: {len([r for r in rows if not r.get('google_maps_url', '').strip()])}")

# Wilaya analysis
by_wilaya = {}
for r in unique_rows:
    w = r.get('wilaya', '').strip()
    if w not in by_wilaya:
        by_wilaya[w] = {'total': 0, 'categories': {}}
    by_wilaya[w]['total'] += 1
    cat = r.get('categorie_recherche', '').strip()
    if cat not in by_wilaya[w]['categories']:
        by_wilaya[w]['categories'][cat] = 0
    by_wilaya[w]['categories'][cat] += 1

print("\n=== COUVERTURE PAR WILAYA (triée par volume croissant) ===")
sorted_wilayas = sorted(by_wilaya.items(), key=lambda x: x[1]['total'])
for w, data in sorted_wilayas:
    cats = len(data['categories'])
    gps = sum(1 for r in unique_rows if r.get('wilaya', '').strip() == w and r.get('latitude', '').strip())
    tel = sum(1 for r in unique_rows if r.get('wilaya', '').strip() == w and r.get('telephone', '').strip())
    print(f"  {w}: {data['total']} entrées, {cats} catégories, GPS={gps}, Tel={tel}")

# Category analysis (national level)
by_cat = {}
for r in unique_rows:
    cat = r.get('categorie_recherche', '').strip()
    if cat not in by_cat:
        by_cat[cat] = {'total': 0, 'phones': 0, 'gps': 0, 'urls': 0, 'place_ids': 0}
    by_cat[cat]['total'] += 1
    if r.get('telephone', '').strip():
        by_cat[cat]['phones'] += 1
    if r.get('latitude', '').strip():
        by_cat[cat]['gps'] += 1
    if r.get('google_maps_url', '').strip():
        by_cat[cat]['urls'] += 1
    if r.get('place_id_si_visible', '').strip():
        by_cat[cat]['place_ids'] += 1

print("\n=== ANALYSE PAR CATÉGORIE (triée par volume croissant) ===")
sorted_cats = sorted(by_cat.items(), key=lambda x: x[1]['total'])
for c, data in sorted_cats:
    print(f"  {c}: {data['total']} entrées, tels={data['phones']}, GPS={data['gps']}")

# Gap analysis per wilaya
print("\n=== ANALYSE DÉFICIT PAR WILAYA ===")
target = 33001
current_total = len(url_seen)
deficit = target - current_total
print(f"  Total actuel (unique URL): {current_total}")
print(f"  Déficit pour 33,001: {deficit}")

# How many entries needed per wilaya to reach 33k equally?
print(f"\n  Si on visait 33,001 réparties sur 58 wilayas: ~{target//58} par wilaya")

# Wilayas with least data (need augmentation)
print("\n=== WILAYAS SOUS-CONTRÔLÉES (moins de 200 entrées) ===")
low_wilayas = [(w, d['total']) for w, d in sorted_wilayas if d['total'] < 200]
for w, t in low_wilayas:
    print(f"  {w}: {t} entrées -> besoin de ~{max(0, 600 - t)} supplémentaires pour atteindre 600")

# Categories with least data
print("\n=== CATÉGORIES SOUS-REPRÉSENTÉES (moins de 200 entrées) ===")
low_cats = [(c, d['total']) for c, d in sorted_cats if d['total'] < 200]
for c, t in low_cats:
    print(f"  {c}: {t} entrées -> besoin de ~{max(0, 400 - t)} supplémentaires pour atteindre 400")
