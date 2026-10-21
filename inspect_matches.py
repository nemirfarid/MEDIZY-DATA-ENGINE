import csv

with open(r'D:\SANTE_DZ_EXPORTS\miph_crossref_matched.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Show 10 sample matches
for r in rows[:10]:
    print(f"PDF: {r['etab_fr'][:55]}")
    print(f"DB:  {r['db_nom'][:55]}")
    print(f"  Match: {r['match_status']}")
    print(f"  DB addr: {r['db_adresse'][:70] if r['db_adresse'] else '---'}")
    print(f"  DB phone: {r['db_telephone'][:30] if r['db_telephone'] else '---'}")
    print(f"  DB site: {r['db_site_web'][:50] if r['db_site_web'] else '---'}")
    print(f"  DB note: {r['db_note']}")
    print()

print(f"\nTotal matched: {len(rows)}")
print(f"Exact: {sum(1 for r in rows if r['match_status'] == 'exact')}")
print(f"Partial: {sum(1 for r in rows if r['match_status'] == 'partial')}")

# Check fields that are missing in DB for matched entries
missing_addr = sum(1 for r in rows if not r['db_adresse'] or r['db_adresse'] == '-')
missing_phone = sum(1 for r in rows if not r['db_telephone'] or r['db_telephone'] == '-')
missing_site = sum(1 for r in rows if not r['db_site_web'])
missing_note = sum(1 for r in rows if not r['db_note'] or r['db_note'] == '-')

print(f"\nFields missing in matched DB entries:")
print(f"  Address:    {missing_addr}/{len(rows)} ({100*missing_addr/len(rows):.1f}%)")
print(f"  Phone:      {missing_phone}/{len(rows)} ({100*missing_phone/len(rows):.1f}%)")
print(f"  Website:    {missing_site}/{len(rows)} ({100*missing_site/len(rows):.1f}%)")
print(f"  Note:       {missing_note}/{len(rows)} ({100*missing_note/len(rows):.1f}%)")

# Check MIPH data quality
miph_missing_postal = sum(1 for r in rows if r['code_postal'] == '0')
print(f"\nMIPH entries with missing postal code: {miph_missing_postal}/{len(rows)} ({100*miph_missing_postal/len(rows):.1f}%)")

# What types of establishments are missing
type_counts = {}
for r in rows:
    t = r['type_etab'] if 'type_etab' in r and r['type_etab'] else 'unknown'
    type_counts[t] = type_counts.get(t, 0) + 1
print("\nType breakdown in cross-ref:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")
