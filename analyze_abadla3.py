# Mission 1: Analyse complète Abadla
import sqlite3
import csv

def safe(s):
    if s is None:
        return ''
    return str(s).encode('ascii', 'replace').decode()

TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db'
GEO_CSV = r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv'

# Check CSV entries
print("=== CSV entries for 08-eph-02 ===")
with open(GEO_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['id'] in ('08-eph-02', '08-epsp-01'):
            print(f"geo_id: {row['id']}")
            print(f"  name_fr: {safe(row['name_fr'])}")
            print(f"  name_ar: {safe(row['name_ar'])}")
            print(f"  wilaya_code: {row['wilaya_code']}")
            print(f"  commune: {safe(row['commune'])}")
            print(f"  type: {row['type']}")
            print(f"  lat: {row['lat']} lng: {row['lng']}")
            print(f"  geo_precision: {row['geo_precision']} geo_method: {row['geo_method']}")
            print()