import csv

with open(r'D:\SANTE_DZ_EXPORTS\miph_crossref_matched.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print("Sample matched entries (showing match quality):")
print("=" * 100)
for r in rows[:30]:
    pdf = r['etab_fr'][:55]
    db = r['db_nom'][:55]
    w = r['wilaya']
    addr = r['db_adresse'][:40] if r['db_adresse'] else '---'
    phone = r['db_telephone'][:20] if r['db_telephone'] else '---'
    note = r['db_note'] if r['db_note'] else '-'
    print(f"  PDF: '{pdf}' ({w}) - [{r['type_etab']}]")
    print(f"  DB:  '{db}' ({r['db_wilaya']}) - [{r['db_categorie']}] note={note}")
    print(f"  Addr: {addr[:55]}")
    print(f"  Phone: {phone}")
    print()

# Count by match quality - how many have the same wilaya
same_wilaya = sum(1 for r in rows if r['wilaya'] == r['db_wilaya'])
diff_wilaya = len(rows) - same_wilaya
print(f"\nWilaya consistency in matches: {same_wilaya}/{len(rows)} same, {diff_wilaya} different")

# Show mismatched wilayas
for r in rows:
    if r['wilaya'] != r['db_wilaya']:
        print(f"  MISMATCH: PDF '{r['etab_fr'][:45]}' PDF wilaya={r['wilaya']} DB wilaya={r['db_wilaya']}")
