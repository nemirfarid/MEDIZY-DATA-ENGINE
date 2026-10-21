#!/usr/bin/env Python3
"""
Phase 4: Validation globale - croisement checkpoint vs DB vs enrichment CSV.
Vérifie si des entrées supplémentaires peuvent être récupérées.
"""
import csv, json, sqlite3, os
from pathlib import Path

CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
ENRICHMENT = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
SEPT_CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'

print("=== ANALYSE COMPLÈTE DES SOURCES ===\n")

# 1. Count entries in each source
sources = {
    'checkpoint.csv': CHECKPOINT,
    'checkpoint_enrichment.csv': ENRICHMENT,
    'checkpoint_20260926.csv': SEPT_CHECKPOINT,
}

for name, path in sources.items():
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            urls = set(r.get('google_maps_url', '').strip() for r in rows if r.get('google_maps_url', '').strip())
            print(f"{name}:")
            print(f"  Rows: {len(rows)}")
            print(f"  Unique URLs: {len(urls)}")
            print(f"  Columns: {reader.fieldnames}")
            print()
    else:
        print(f"{name}: FILE NOT FOUND\n")

# 2. Compare DB with checkpoint
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM places")
db_count = cur.fetchone()[0]

# Get all URLs in DB
cur.execute("SELECT google_maps_url FROM places WHERE google_maps_url IS NOT NULL")
db_urls = set(r[0] for r in cur.fetchall())

# Get valid URLs from checkpoint (non-CANDIDATE)
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    checkpoint_urls = set()
    checkpoint_url_status = {}  # url -> name_status
    for r in reader:
        url = r.get('google_maps_url', '').strip()
        if url:
            checkpoint_urls.add(url)
            checkpoint_url_status[url] = r.get('name_status', 'VERIFIED')

print(f"DB total: {db_count}")
print(f"DB URLs: {len(db_urls)}")
print(f"Checkpoint URLs (all): {len(checkpoint_urls)}")

# How many checkpoint URLs are in DB
in_db = checkpoint_urls & db_urls
print(f"Checkpoint URLs in DB: {len(in_db)}")
print(f"Checkpoint URLs NOT in DB: {len(checkpoint_urls - db_urls)}")

# Check the ones not in DB - are they candidates?
not_in_db = checkpoint_urls - db_urls
candidate_urls = [u for u in not_in_db if checkpoint_url_status.get(u, 'VERIFIED') == 'CANDIDATE']
non_candidate_not_in_db = [u for u in not_in_db if checkpoint_url_status.get(u, 'VERIFIED') != 'CANDIDATE']
print(f"  Of those, CANDIDATE: {len(candidate_urls)}")
print(f"  Of those, non-CANDIDATE: {len(non_candidate_not_in_db)}")

conn.close()
