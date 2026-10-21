import csv
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\SANTE_DZ_EXPORTS\miph_parsed_all.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    zero_postal = [r for r in rows if r.get('code_postal', '').strip() in ('0', '00000', '')]
    print(f'Total MIPH entries: {len(rows)}')
    print(f'Entries with postal code 0 or empty: {len(zero_postal)}')
    for r in zero_postal[:20]:
        print(f'  {r["pdf_id"]}: {r["type_etab"]} - {r["etab_fr"]} (Wilaya: {r["wilaya"]}, Postal: {r["code_postal"]})')