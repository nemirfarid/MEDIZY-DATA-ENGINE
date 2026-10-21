import csv
import sqlite3

# Load GeoAlgeria data
with open(r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    geo_rows = list(reader)

print("=" * 80)
print("AUDIT GEOALGERIA SANTE - NATIONAL")
print("=" * 80)
print("Total lignes: {}".format(len(geo_rows)))
print("Colonnes: {}".format(reader.fieldnames))

# Wilaya distribution
wilaya_counts = {}
for r in geo_rows:
    wilaya_counts[r['wilaya_code']] = wilaya_counts.get(r['wilaya_code'], 0) + 1

print("\nRepartition par wilaya:")
for wc in sorted(wilaya_counts.keys(), key=int):
    print("  {}: {}".format(wc, wilaya_counts[wc]))

# Type distribution
type_counts = {}
for r in geo_rows:
    type_counts[r['type']] = type_counts.get(r['type'], 0) + 1

print("\nRepartition par type:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(t, c))

# GPS coverage
with_gps = sum(1 for r in geo_rows if r['lat'] and r['lng'])
print("\nCouverture GPS: {}/{} ({:.1f}%)".format(with_gps, len(geo_rows), with_gps*100/len(geo_rows)))

# Source distribution
source_counts = {}
for r in geo_rows:
    s = r['source'] or 'inconnu'
    source_counts[s] = source_counts.get(s, 0) + 1
print("\nSources:")
for s, c in sorted(source_counts.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(s, c))

# Geo method
method_counts = {}
for r in geo_rows:
    m = r['geo_method'] or 'inconnu'
    method_counts[m] = method_counts.get(m, 0) + 1
print("\nMethodes de geocodage:")
for m, c in sorted(method_counts.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(m, c))

# Precision
precision_counts = {}
for r in geo_rows:
    p = r['geo_precision'] or 'inconnu'
    precision_counts[p] = precision_counts.get(p, 0) + 1
print("\nPrecision:")
for p, c in sorted(precision_counts.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(p, c))

# Missing commune
missing_commune = sum(1 for r in geo_rows if not r['commune'] or r['commune'].strip() == '')
print("\nCommunes manquantes: {}".format(missing_commune))

conn.close()