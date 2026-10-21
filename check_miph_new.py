import csv
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\SANTE_DZ_EXPORTS\miph_crossref_new.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    print(f'miph_crossref_new.csv: {len(rows)} rows')
    print('Columns:', list(rows[0].keys()))
    for i, row in enumerate(rows):
        print(f'  {row["pdf_id"]}: {row["type_etab"]} - {row["etab_fr"]} (Wilaya: {row["wilaya"]}, Code: {row["wilaya_code"]}, Postal: {row["code_postal"]})')