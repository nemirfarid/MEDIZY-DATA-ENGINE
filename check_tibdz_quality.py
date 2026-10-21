import csv
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Check tibdz_enriched.csv for suspicious data
with open(r'D:\SANTE_DZ_EXPORTS\tibdz_enriched.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    print(f"Total enriched entries: {len(rows)}")
    
    phones = set()
    sites = set()
    for row in rows:
        phones.add(row['phone'])
        sites.add(row['website'])
    
    print(f"Unique phones: {len(phones)}")
    for p in phones:
        print(f"  Phone: {p}")
    
    print(f"Unique websites: {len(sites)}")
    for s in sites:
        print(f"  Site: {s}")