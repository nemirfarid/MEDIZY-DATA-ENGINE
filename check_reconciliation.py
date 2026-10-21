import csv
from collections import Counter

def safe(s):
    if s is None:
        return ''
    return str(s).encode('ascii', 'replace').decode()

with open(r'C:\SANTE_DZ_SCRAPER\phase6_5_1_reconciliation.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Check the 4 non-classified
non_class = [r for r in rows if r['classification_status'] == 'NON CLASSIFIÉ']
print("Entrées NON CLASSIFIÉ: {}".format(len(non_class)))
for r in non_class:
    print("  place_id={} | geo_id={}".format(r['place_id'], r['geo_id']))
    print("    FR_DB: {}".format(safe(r['nom_fr_db'])))
    print("    FR_CSV: {}".format(safe(r['nom_fr_csv'])))
    print("    AR_CSV: {}".format(safe(r['nom_ar_csv'][:80])))
    print("    Anomalies: {}".format(safe(r['anomalies'])))
    print()

# Check all statuses
status = Counter(r['classification_status'] for r in rows)
print("Statuts: {}".format(dict(status)))

# Check in_csv_source
in_csv = Counter(r['in_csv_source'] for r in rows)
print("in_csv_source: {}".format(dict(in_csv)))

# Check in_classification
in_class = Counter(r['in_classification'] for r in rows)
print("in_classification: {}".format(dict(in_class)))

# Check the 2 with empty FR in CSV
empty_fr = [r for r in rows if not r['nom_fr_csv'].strip()]
print("\nNoms FR vides dans CSV: {}".format(len(empty_fr)))
for r in empty_fr:
    print("  place_id={} | geo_id={} | AR={}".format(r['place_id'], r['geo_id'], safe(r['nom_ar_csv'][:80])))

# Check for ???? in Arabic names
arabic_issues = [r for r in rows if '????' in r['nom_ar_csv']]
print("\nNoms arabes avec ????: {}".format(len(arabic_issues)))
for r in arabic_issues:
    print("  place_id={} | geo_id={} | AR={}".format(r['place_id'], r['geo_id'], safe(r['nom_ar_csv'][:100])))