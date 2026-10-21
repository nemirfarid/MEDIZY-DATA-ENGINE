"""Check tibdz enrichment results."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os, csv

f2 = r'D:\SANTE_DZ_EXPORTS\tibdz_enriched.csv'
if os.path.exists(f2):
    with open(f2, encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    print(f'tibdz_enriched.csv: {len(rows)} entries')
    for r in rows[:5]:
        name = r.get('db_name', '')[:50]
        tel = r.get('phone', '')
        site = r.get('website', '')[:50]
        print(f'  {name} -> tel={tel}, site={site}')
else:
    print('tibdz_enriched.csv: NOT FOUND')
    f1 = r'D:\SANTE_DZ_EXPORTS\tibdz_all_entries.csv'
    print(f'tibdz_all_entries exists: {os.path.exists(f1)}')
