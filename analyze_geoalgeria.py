import csv

with open(r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total rows: {len(reader.fieldnames)} columns, {len(rows)} data rows")
print(f"Columns: {reader.fieldnames}")

# Filter Biskra (wilaya_code 07)
biskra = [r for r in rows if r['wilaya_code'] == '07']
print(f"\nBiskra entries: {len(biskra)}")
for r in biskra:
    name = r['name_fr'] or r['name'] or 'N/A'
    # ASCII-safe output
    safe_name = name.encode('ascii', 'replace').decode()
    safe_commune = (r['commune'] or '').encode('ascii', 'replace').decode()
    print(f"  {r['id']}: {safe_name} | type={r['type']} | commune={safe_commune} | lat={r['lat']} | lng={r['lng']} | precision={r['geo_precision']} | method={r['geo_method']}")

# Also check all wilayas distribution
wilaya_counts = {}
for r in rows:
    wilaya_counts[r['wilaya_code']] = wilaya_counts.get(r['wilaya_code'], 0) + 1

print("\nAll wilayas:")
for wc in sorted(wilaya_counts.keys(), key=int):
    print(f"  {wc}: {wilaya_counts[wc]}")

# Type distribution
type_counts = {}
for r in rows:
    type_counts[r['type']] = type_counts.get(r['type'], 0) + 1

print("\nType distribution:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")