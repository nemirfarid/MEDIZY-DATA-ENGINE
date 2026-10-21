import csv
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\SANTE_DZ_EXPORTS\geocoding_review_pending.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i < 5:
            print(dict(row))
        if 'Naama' in row.get('wilaya', '') or 'Na' in row.get('wilaya', ''):
            print('NAAMA:', dict(row))
        if 'Cabinet' in row.get('nom', '') and 'chirurgical' in row.get('nom', '').lower():
            print('CHIRURGICAL:', dict(row))
        if 'Medico' in row.get('nom', '') or 'medico' in row.get('nom', '').lower():
            print('MEDICO:', dict(row))