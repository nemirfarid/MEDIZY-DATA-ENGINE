#!/usr/bin/env python3
"""Investigate potential data loss between old DB and current checkpoint."""
import csv, sqlite3, sys
from collections import Counter

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load current checkpoint URLs
csv_path = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)
csv_urls = set(r['google_maps_url'].strip() for r in csv_rows if r.get('google_maps_url', '').strip())

# Load old DB URLs
old_db = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_20261010_014940.db'
conn = sqlite3.connect(old_db)
cursor = conn.cursor()
cursor.execute('SELECT google_maps_url FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != ""')
old_urls = set(r[0] for r in cursor.fetchall())

# Get full rows from old DB that are NOT in CSV
missing_urls = old_urls - csv_urls
print(f"URLs dans old DB mais PAS dans CSV: {len(missing_urls)}")

# Get details for samples
sample = list(missing_urls)[:5]
for url in sample:
    cursor.execute('SELECT nom, wilaya, commune, categorie_recherche, telephone, adresse, note FROM places WHERE google_maps_url = ?', (url,))
    row = cursor.fetchone()
    if row:
        print(f"\n  Nom: {row[0]}")
        print(f"  Wilaya: {row[1]}")
        print(f"  Categorie: {row[3]}")
        print(f"  Tel: {row[4]}")
        print(f"  Note: {row[6]}")

# Check which wilayas are affected
print("\n=== Wilayas des URLs manquantes (old DB -> CSV) ===")
wilaya_counter = Counter()
for url in missing_urls:
    cursor.execute('SELECT wilaya FROM places WHERE google_maps_url = ?', (url,))
    row = cursor.fetchone()
    if row:
        wilaya_counter[row[0]] += 1

for w, c in wilaya_counter.most_common():
    print(f"  {w}: {c} URLs manquantes")

# Also check place_ids
cursor.execute('SELECT place_id FROM places WHERE place_id IS NOT NULL AND place_id != ""')
old_pids = set(r[0] for r in cursor.fetchall())
csv_pids = set(r['place_id_si_visible'].strip() for r in csv_rows if r.get('place_id_si_visible', '').strip())
missing_pids = old_pids - csv_pids
print(f"\nplace_ids dans old DB mais PAS dans CSV: {len(missing_pids)}")

conn.close()

# Check if these missing URLs/IDs exist in any other source file
print("\n=== Verification des URLs manquantes dans d'autres sources ===")

# Check snapshot
snap_path = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
with open(snap_path, 'r', encoding='utf-8-sig') as f:
    snap_rows = list(csv.DictReader(f))
snap_urls = set(r['google_maps_url'].strip() for r in snap_rows if r.get('google_maps_url', '').strip())
in_snap_missing = missing_urls & snap_urls
print(f"  Dans snapshot sept 26: {len(in_snap_missing)} des URLs manquantes")

# Check enrichment checkpoint
rich_path = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
with open(rich_path, 'r', encoding='utf-8-sig') as f:
    rich_rows = list(csv.DictReader(f))
rich_urls = set(r['google_maps_url'].strip() for r in rich_rows if r.get('google_maps_url', '').strip())
in_rich_missing = missing_urls & rich_urls
print(f"  Dans checkpoint_enrichment: {len(in_rich_missing)} des URLs manquantes")

# Check National CSV
nat_csv = r'D:\SANTE_DZ_EXPORTS\SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv'
with open(nat_csv, 'r', encoding='utf-8-sig') as f:
    nat_rows = list(csv.DictReader(f))
nat_urls = set(r['google_maps_url'].strip() for r in nat_rows if r.get('google_maps_url', '').strip())
in_nat_missing = missing_urls & nat_urls
print(f"  Dans SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv: {len(in_nat_missing)} des URLs manquantes")

# Summary
all_sources_urls = snap_urls | rich_urls | nat_urls | csv_urls
print(f"\n=== SUMMARY ===")
print(f"  TOTAL URLs manquantes (old DB not in CSV): {len(missing_urls)}")
print(f"  TOTAL place_ids manquants (old DB not in CSV): {len(missing_pids)}")
print(f"  URLs manquantes retrouvees dans au moins une source: {len(missing_urls & all_sources_urls)}")
print(f"  URLs manquantes NON retrouvees nulle part: {len(missing_urls - all_sources_urls)}")

# Check if these missing URLs have same place_id in CSV (cross-reference)
print(f"\n=== Cross-reference missing URLs vs CSV place_ids ===")
for url in list(missing_urls)[:3]:
    cursor = sqlite3.connect(old_db).cursor()
    cursor.execute('SELECT place_id FROM places WHERE google_maps_url = ?', (url,))
    row = cursor.fetchone()
    if row and row[0]:
        pid = row[0]
        in_csv = pid in csv_pids
        print(f"  URL: {url[:60]}...")
        print(f"  place_id: {pid}")
        print(f"  place_id dans CSV: {in_csv}")
