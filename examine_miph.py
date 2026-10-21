import csv

f = open(r'D:\SANTE_DZ_EXPORTS\miph_crossref_new.csv', 'r', encoding='utf-8-sig')
reader = csv.DictReader(f)
rows = list(reader)
print('Columns:', reader.fieldnames)
print('Total rows:', len(rows))
print('First 3 rows (ascii-safe):')
for r in rows[:3]:
    safe = {k: v.encode('ascii', 'replace').decode() for k, v in r.items()}
    print(safe)

# Check postal codes
postal_codes = set()
for r in rows:
    postal_codes.add(r['code_postal'])
print('\nUnique postal codes:', sorted(postal_codes))

# Count postal_code = 0
zero_count = sum(1 for r in rows if r['code_postal'].strip() in ('0', '00000', ''))
print(f'Postal code = 0 or empty: {zero_count}')

# Show all rows with postal_code = 0
print('\nRows with postal_code = 0:')
for r in rows:
    if r['code_postal'].strip() in ('0', '00000', ''):
        safe = {k: v.encode('ascii', 'replace').decode() for k, v in r.items()}
        print(safe)

f.close()