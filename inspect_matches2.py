import csv

with open(r'D:\SANTE_DZ_EXPORTS\miph_crossref_matched.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

exact = [r for r in rows if r['match_status'] == 'exact']
print(f'Exact matches: {len(exact)}')
for r in exact[:5]:
    print(repr(r['etab_fr']), '->', repr(r['db_nom']))

partial = [r for r in rows if r['match_status'] == 'partial']
print(f'\nPartial matches: {len(partial)}')
for r in partial[:15]:
    print(f'PDF: {repr(r["etab_fr"][:70])}')
    print(f'DB:  {repr(r["db_nom"][:70])}')
    print()
