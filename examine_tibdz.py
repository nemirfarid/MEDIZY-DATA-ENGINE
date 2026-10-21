import csv

f = open(r'D:\SANTE_DZ_EXPORTS\tibdz_enriched.csv', 'r', encoding='utf-8')
reader = csv.DictReader(f)
rows = list(reader)
print('Columns:', reader.fieldnames)
print('Total rows:', len(rows))

# Check phones and websites
phones = set()
sites = set()
for r in rows:
    phones.add(r['phone'])
    sites.add(r['website'])

print('\nUnique phones:', phones)
print('Unique websites:', sites)

# Show first 5 rows
print('\nFirst 5 rows:')
for r in rows[:5]:
    print(r)

f.close()