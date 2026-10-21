#!/usr/bin/env Python3
"""
Phase 5 — Étape 3: Re-examine why only 22 of 674 candidate entries were imported.
Check for internal duplicates (same place_id or URL within the candidate set).
"""
import sqlite3, csv, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
EXTRACTED_FILE = r'D:\SANTE_DZ_EXPORTS\candidate_names_extracted.csv'

# Load extracted names
with open(EXTRACTED_FILE, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    extracted = list(reader)

# Load CANDIDATE rows
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    ckpt_rows = list(reader)

candidates = [r for r in ckpt_rows if r.get('name_status', 'VERIFIED') == 'CANDIDATE']
print(f"CANDIDATE in checkpoint: {len(candidates)}")

# Build candidate URL -> full row
candidate_map = {}
for r in candidates:
    url = r.get('google_maps_url', '').strip()
    if url:
        candidate_map[url] = r

# Build set of URLs in DB
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT google_maps_url FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != ''")
db_urls = set(r[0] for r in cur.fetchall())
cur.execute("SELECT place_id FROM places WHERE place_id IS NOT NULL AND place_id != ''")
db_pids = set(r[0] for r in cur.fetchall())
conn.close()

# Find entries NOT in DB
new_urls = []
new_rows = []
for e in extracted:
    url = ''
    for c in candidates:
        if c.get('nom', '') == e.get('nom_original', '') and c.get('wilaya', '') == e.get('wilaya', ''):
            url = c.get('google_maps_url', '').strip()
            break
    
    if not url or url in db_urls:
        continue
    
    c = candidate_map.get(url, {})
    pid = c.get('place_id_si_visible', '').strip()
    if pid and pid in db_pids:
        continue
    
    new_urls.append(url)
    new_rows.append({'url': url, 'pid': pid, 'nom': e['nom_recupere'], 'candidate': c})

print(f"New URLs (not in DB): {len(new_urls)}")

# Check for internal duplicates
from collections import Counter
url_counts = Counter(new_urls)
internal_url_dups = {u: c for u, c in url_counts.items() if c > 1}
print(f"Internal URL duplicates: {len(internal_url_dups)} URLs with count > 1")
print(f"Total duplicate rows: {sum(c-1 for c in internal_url_dups.values())}")

pid_counts = Counter(r['pid'] for r in new_rows if r['pid'])
internal_pid_dups = {p: c for p, c in pid_counts.items() if c > 1}
print(f"Internal place_id duplicates: {len(internal_pid_dups)} place_ids with count > 1")
print(f"Total duplicate rows by PID: {sum(c-1 for c in internal_pid_dups.values())}")

# Show top URL duplicates
print(f"\n=== Top 5 URL duplicates ===")
for url, count in list(internal_url_dups.items())[:5]:
    print(f"  URL appears {count} times:")
    for r in new_rows:
        if r['url'] == url:
            print(f"    Nom: {r['nom'][:40]}, PID: {r['pid'][:30]}")

# Check: how many unique URLs and place_ids?
unique_urls = set(new_urls)
unique_pids = set(r['pid'] for r in new_rows if r['pid'])
print(f"\nUnique URLs in new set: {len(unique_urls)}")
print(f"Unique place_ids in new set: {len(unique_pids)}")

# What would import if we dedup by URL?
print(f"\nIf dedup by URL: {len(unique_urls)} entries would be imported")
print(f"If dedup by place_id: {len(unique_pids)} entries would be imported")
print(f"Union (either unique): {len(unique_urls | set(r['pid'] for r in new_rows if r['pid']))}")

# Check if place_ids exist in DB
cur.execute("SELECT place_id FROM places WHERE place_id IS NOT NULL AND place_id != ''")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT place_id FROM places WHERE place_id IS NOT NULL AND place_id != ''")
db_pids = set(r[0] for r in cur.fetchall())
conn.close()

new_pids_in_db = [pid for pid in unique_pids if pid in db_pids]
new_pids_not_in_db = [pid for pid in unique_pids if pid not in db_pids and pid]
print(f"\nUnique new place_ids already in DB: {len(new_pids_in_db)}")
print(f"Unique new place_ids NOT in DB: {len(new_pids_not_in_db)}")

# The real count of importable entries
# A URL is importable if: it's not in DB, AND its place_id (if any) is not in DB
truly_new = []
for r in new_rows:
    url = r['url']
    pid = r['pid']
    if url in db_urls:
        continue
    if pid and pid in db_pids:
        continue
    truly_new.append(r)

# Deduplicate by URL
truly_new_by_url = {}
for r in truly_new:
    if r['url'] not in truly_new_by_url:
        truly_new_by_url[r['url']] = r

print(f"\n=== VRAIE IMPORTABLE COUNT ===")
print(f"After URL dedup and place_id check: {len(truly_new_by_url)} entries")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM places")
db_before = cur.fetchone()[0]
print(f"DB before: {db_before}")
conn.close()
