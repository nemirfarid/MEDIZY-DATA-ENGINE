#!/usr/bin/env python3
"""Compute total unique entries across ALL sources."""
import csv, sqlite3, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def load_csv_urls(path):
    """Load URLs from a CSV file."""
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    urls = set()
    pids = set()
    data = []
    for r in rows:
        url = r.get('google_maps_url', '').strip()
        pid = r.get('place_id_si_visible', '').strip()
        if url:
            urls.add(url)
        if pid:
            pids.add(pid)
        data.append(r)
    return rows, urls, pids

# Load all CSV sources
print("=== CHARGEMENT DES SOURCES ===")

# Source 1: checkpoint.csv
csv_rows, csv_urls, csv_pids = load_csv_urls(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv')
print(f"checkpoint.csv: {len(csv_rows)} rows, {len(csv_urls)} URLs, {len(csv_pids)} place_ids")

# Source 2: checkpoint_enrichment.csv
rich_rows, rich_urls, rich_pids = load_csv_urls(r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv')
print(f"checkpoint_enrichment.csv: {len(rich_rows)} rows, {len(rich_urls)} URLs, {len(rich_pids)} place_ids")

# Source 3: snapshot
snap_rows, snap_urls, snap_pids = load_csv_urls(r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv')
print(f"checkpoint_20260926 snapshot: {len(snap_rows)} rows, {len(snap_urls)} URLs, {len(snap_pids)} place_ids")

# Source 4: National CSV
nat_rows, nat_urls, nat_pids = load_csv_urls(r'D:\SANTE_DZ_EXPORTS\SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv')
print(f"SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv: {len(nat_rows)} rows, {len(nat_urls)} URLs, {len(nat_pids)} place_ids")

# Source 5: Old DB
old_db = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_20261010_014940.db'
conn = sqlite3.connect(old_db)
cursor = conn.cursor()
cursor.execute('SELECT google_maps_url, place_id FROM places WHERE (google_maps_url IS NOT NULL AND google_maps_url != "") OR (place_id IS NOT NULL AND place_id != "")')
old_data = cursor.fetchall()
old_urls = set(url for url, pid in old_data if url)
old_pids = set(pid for url, pid in old_data if pid)
conn.close()
print(f"old DB backup: {len(old_data)} rows, {len(old_urls)} URLs, {len(old_pids)} place_ids")

# Source 6: Current DB
curr_db = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
conn = sqlite3.connect(curr_db)
cursor = conn.cursor()
cursor.execute('SELECT google_maps_url, place_id FROM places WHERE (google_maps_url IS NOT NULL AND google_maps_url != "") OR (place_id IS NOT NULL AND place_id != "")')
curr_data = cursor.fetchall()
curr_urls = set(url for url, pid in curr_data if url)
curr_pids = set(pid for url, pid in curr_data if pid)
conn.close()
print(f"current DB: {len(curr_data)} rows, {len(curr_urls)} URLs, {len(curr_pids)} place_ids")

# ============================================================================
# UNION ANALYSIS
# ============================================================================
print("\n" + "=" * 70)
print("ANALYSE DE L'UNION DE TOUTES LES SOURCES")
print("=" * 70)

all_urls = csv_urls | rich_urls | snap_urls | nat_urls | old_urls | curr_urls
print(f"Total URLs uniques dans TOUTES sources: {len(all_urls)}")

# Which URLs are in the current DB but nowhere in CSV sources?
missing_from_csv = curr_urls - (csv_urls | rich_urls | snap_urls | nat_urls | old_urls)
print(f"URLs dans DB mais NULLE PART dans CSV sources: {len(missing_from_csv)}")

# Which CSV URLs are NOT in DB?
csv_urls_not_in_db = csv_urls - curr_urls
print(f"URLs dans CSV mais PAS dans DB: {len(csv_urls_not_in_db)}")

# Which old DB URLs are NOT in current CSV?
old_urls_not_csv = old_urls - csv_urls
print(f"URLs dans old DB mais PAS dans CSV actuel: {len(old_urls_not_csv)}")

# Recovery potential: entries from enrichment checkpoint not in current CSV
recoverable_from_enrichment = rich_urls - csv_urls
print(f"URLs récupérables depuis enrichment (pas dans CSV): {len(recoverable_from_enrichment)}")

# Recovery potential: entries from old DB not in current CSV
recoverable_from_old = old_urls - csv_urls
print(f"URLs récupérables depuis old DB (pas dans CSV): {len(recoverable_from_old)}")

# Recovery potential: entries from snapshot not in current CSV
recoverable_from_snap = snap_urls - csv_urls
print(f"URLs récupérables depuis snapshot (pas dans CSV): {len(recoverable_from_snap)}")

# Total recoverable (not in current CSV, but found in other sources)
recoverable = (rich_urls | snap_urls | old_urls) - csv_urls
print(f"\nURLs récupérables totales (pas dans CSV, mais dans d'autres sources): {len(recoverable)}")

# Potential total unique if we merge everything
potential_total = csv_urls | recoverable
print(f"Potentiel total unique (CSV + récupérables): {len(potential_total)}")

# Deficit to 33,001
print(f"\n=== DÉFICIT ===")
print(f"Current SQLite DB entries (unique by URL): {len(curr_urls)}")
print(f"Current checkpoint unique URLs: {len(csv_urls)}")
print(f"Potential total with recovery: {len(potential_total)}")
print(f"Déficit après récupération (33,001 - potential): {33001 - len(potential_total)}")

# Breakdown of recoverable by wilaya
print("\n=== Répartition des URLs récupérables par wilaya ===")
recoverable_by_wilaya = Counter()
all_enrich_rows = {r['google_maps_url'].strip(): r for r in rich_rows if r.get('google_maps_url', '').strip()}
all_snap_rows = {r['google_maps_url'].strip(): r for r in snap_rows if r.get('google_maps_url', '').strip()}
all_old_rows = {}  # We'll get from DB

# Get old DB rows for recoverable URLs
conn = sqlite3.connect(old_db)
cursor = conn.cursor()
for url in recoverable:
    cursor.execute('SELECT wilaya FROM places WHERE google_maps_url = ?', (url,))
    row = cursor.fetchone()
    if row:
        recoverable_by_wilaya[row[0]] += 1
conn.close()

# Also check enrichment rows
for url in recoverable:
    if url in all_enrich_rows:
        w = all_enrich_rows[url].get('wilaya', 'unknown').strip()
        recoverable_by_wilaya[w] += 0  # Don't double-count, already counted from old DB

for w, c in recoverable_by_wilaya.most_common():
    print(f"  {w}: {c}")

print(f"\n  TOTAL récupérables: {sum(recoverable_by_wilaya.values())}")
