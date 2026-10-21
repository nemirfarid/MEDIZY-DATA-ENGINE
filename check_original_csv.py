import csv

def safe(s):
    if s is None:
        return ''
    return str(s).encode('ascii', 'replace').decode()

with open(r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['id'] in ('21-eph-08', '19-epsp-10', '08-eph-02', '48-eph-01'):
            print('geo_id:', row['id'])
            print('  name_fr:', repr(row['name_fr']))
            print('  name_ar:', safe(repr(row['name_ar'])))
            print('  wilaya_code:', row['wilaya_code'])
            print('  commune:', row['commune'])
            print('  lat:', row['lat'])
            print('  lng:', row['lng'])
            print('  type:', row['type'])
            print('  geo_precision:', row['geo_precision'])
            print('  geo_method:', row['geo_method'])
            print()