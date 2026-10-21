#!/usr/bin/env python3
"""Phase 2 - Analyse détaillée des volumes et déficit."""
import csv, sqlite3, os
from pathlib import Path

print("=" * 70)
print("PHASE 2 — ANALYSE DES VOLUMES ET DÉFICIT")
print("=" * 70)

# ============================================================================
# SOURCE 1: checkpoint.csv (D:\SANTE_DZ_EXPORTS)
# ============================================================================
print("\n" + "=" * 70)
print("SOURCE 1: checkpoint.csv (D:\\SANTE_DZ_EXPORTS\\checkpoint.csv)")
print("=" * 70)

csv_path = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

total_csv = len(rows)
print(f"  Total lignes CSV: {total_csv}")

# Unique par place_id
place_ids_with_values = [r for r in rows if r.get('place_id_si_visible', '').strip()]
place_ids_empty = [r for r in rows if not r.get('place_id_si_visible', '').strip()]
distinct_place_ids = set(r['place_id_si_visible'].strip() for r in rows if r.get('place_id_si_visible', '').strip())
print(f"  Avec place_id non vide: {len(place_ids_with_values)}")
print(f"  Avec place_id vide: {len(place_ids_empty)}")
print(f"  Distinct place_id: {len(distinct_place_ids)}")

# Unique par URL
urls_with_values = [r for r in rows if r.get('google_maps_url', '').strip()]
urls_empty = [r for r in rows if not r.get('google_maps_url', '').strip()]
distinct_urls = set(r['google_maps_url'].strip() for r in rows if r.get('google_maps_url', '').strip())
print(f"  Avec google_maps_url non vide: {len(urls_with_values)}")
print(f"  Avec google_maps_url vide: {len(urls_empty)}")
print(f"  Distinct google_maps_url: {len(distinct_urls)}")

# Unique combinaison (nom + wilaya + adresse)
combos = set()
for r in rows:
    key = (r.get('nom', '').strip(), r.get('wilaya', '').strip(), r.get('adresse', '').strip())
    combos.add(key)
print(f"  Distinct (nom, wilaya, adresse): {len(combos)}")

# Rows with both place_id and url
both_filled = [r for r in rows if r.get('place_id_si_visible', '').strip() and r.get('google_maps_url', '').strip()]
print(f"  Avec place_id ET url remplis: {len(both_filled)}")

# Doublons selon place_id (même place_id, plusieurs lignes)
from collections import Counter
pid_counts = Counter(r['place_id_si_visible'].strip() for r in rows if r.get('place_id_si_visible', '').strip())
multi_pid = {k: v for k, v in pid_counts.items() if v > 1}
print(f"  place_id présents plusieurs fois: {len(multi_pid)} (total lignes concernées: {sum(v for v in multi_pid.values())})")

# Doublons selon URL
url_counts = Counter(r['google_maps_url'].strip() for r in rows if r.get('google_maps_url', '').strip())
multi_url = {k: v for k, v in url_counts.items() if v > 1}
print(f"  url présentes plusieurs fois: {len(multi_url)} (total lignes concernées: {sum(v for v in multi_url.values())})")

# Wilaya breakdown
by_wilaya = Counter(r['wilaya'].strip() for r in rows if r.get('wilaya', '').strip())
print(f"\n  Répartition par wilaya (top 10):")
for w, c in by_wilaya.most_common(10):
    print(f"    {w}: {c}")

# Category breakdown
by_cat = Counter(r['categorie_recherche'].strip() for r in rows if r.get('categorie_recherche', '').strip())
print(f"\n  Répartition par catégorie:")
for c, cnt in sorted(by_cat.items()):
    print(f"    {c}: {cnt}")

# ============================================================================
# SOURCE 2: SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv
# ============================================================================
print("\n" + "=" * 70)
print("SOURCE 2: SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv")
print("=" * 70)

nat_csv = r'D:\SANTE_DZ_EXPORTS\SANTE_DZ_GOOGLE_MAPS_NATIONAL.csv'
with open(nat_csv, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    nat_rows = list(reader)

print(f"  Total lignes: {len(nat_rows)}")

# Check if same as checkpoint
if nat_rows == rows:
    print("  IDENTIQUE au checkpoint.csv")
else:
    nat_urls = set(r['google_maps_url'].strip() for r in nat_rows if r.get('google_maps_url', '').strip())
    csv_urls = set(r['google_maps_url'].strip() for r in rows if r.get('google_maps_url', '').strip())
    print(f"  URLs nationales: {len(nat_urls)}")
    print(f"  URLs checkpoint: {len(csv_urls)}")
    print(f"  Intersection: {len(nat_urls & csv_urls)}")
    print(f"  National only: {len(nat_urls - csv_urls)}")
    print(f"  Checkpoint only: {len(csv_urls - nat_urls)}")

# ============================================================================
# SOURCE 3: snapshot checkpoint_20260926
# ============================================================================
print("\n" + "=" * 70)
print("SOURCE 3: snapshots/checkpoint_20260926_014602.csv")
print("=" * 70)

snap_path = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
if os.path.exists(snap_path):
    with open(snap_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        snap_rows = list(reader)
    snap_urls = set(r['google_maps_url'].strip() for r in snap_rows if r.get('google_maps_url', '').strip())
    print(f"  Total lignes: {len(snap_rows)}")
    print(f"  Distinct URLs: {len(snap_urls)}")
    print(f"  URLs dans checkpoint mais PAS dans snapshot: {len(csv_urls - snap_urls)}")
    print(f"  URLs dans snapshot mais PAS dans checkpoint: {len(snap_urls - csv_urls)}")

# ============================================================================
# SOURCE 4: checkpoint_enrichment.csv
# ============================================================================
print("\n" + "=" * 70)
print("SOURCE 4: checkpoint_enrichment.csv")
print("=" * 70)

rich_path = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
if os.path.exists(rich_path):
    with open(rich_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rich_rows = list(reader)
    rich_urls = set(r['google_maps_url'].strip() for r in rich_rows if r.get('google_maps_url', '').strip())
    print(f"  Total lignes: {len(rich_rows)}")
    print(f"  Distinct URLs: {len(rich_urls)}")
    print(f"  URLs dans checkpoint mais PAS dans enrichment: {len(csv_urls - rich_urls)}")
    print(f"  URLs dans enrichment mais PAS dans checkpoint: {len(rich_urls - csv_urls)}")
    print(f"  Intersection: {len(rich_urls & csv_urls)}")

# ============================================================================
# SOURCE 5: SQLite DB
# ============================================================================
print("\n" + "=" * 70)
print("SOURCE 5: medizy_scraper.db (places table)")
print("=" * 70)

db_path = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM places')
db_total = cursor.fetchone()[0]
print(f"  Total rows: {db_total}")

cursor.execute('SELECT COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) FROM places')
db_gps = cursor.fetchone()[0]
print(f"  Avec GPS: {db_gps}")

cursor.execute('SELECT COUNT(DISTINCT place_id) FROM places')
db_distinct_pid = cursor.fetchone()[0]
print(f"  Distinct place_id: {db_distinct_pid}")

cursor.execute('SELECT COUNT(DISTINCT google_maps_url) FROM places')
db_distinct_url = cursor.fetchone()[0]
print(f"  Distinct google_maps_url: {db_distinct_url}")

# URLs in DB vs CSV
db_urls = set(r[0] for r in cursor.execute('SELECT google_maps_url FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != ""').fetchall())
print(f"  URLs dans DB: {len(db_urls)}")
print(f"  URLs dans CSV mais PAS dans DB: {len(csv_urls - db_urls)}")
print(f"  URLs dans DB mais PAS dans CSV: {len(db_urls - csv_urls)}")

conn.close()

# ============================================================================
# SOURCE 6: Old backup DB (pre-import)
# ============================================================================
print("\n" + "=" * 70)
print("SOURCE 6: backups/medizy_scraper_backup_20261010_014940.db (pre-scraping)")
print("=" * 70)

old_db = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_20261010_014940.db'
conn = sqlite3.connect(old_db)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM places')
old_total = cursor.fetchone()[0]
print(f"  Total rows: {old_total}")
cursor.execute('SELECT COUNT(DISTINCT place_id) FROM places')
old_pid = cursor.fetchone()[0]
print(f"  Distinct place_id: {old_pid}")
cursor.execute('SELECT COUNT(DISTINCT google_maps_url) FROM places')
old_url = cursor.fetchone()[0]
print(f"  Distinct google_maps_url: {old_url}")

# Check if old DB URLs are in current CSV
old_urls = set(r[0] for r in cursor.execute('SELECT google_maps_url FROM places WHERE google_maps_url IS NOT NULL AND google_maps_url != ""').fetchall())
print(f"  URLs dans old DB: {len(old_urls)}")
print(f"  URLs dans CSV mais PAS dans old DB: {len(csv_urls - old_urls)}")
print(f"  URLs dans old DB mais PAS dans CSV: {len(old_urls - csv_urls)}")
print(f"  URLs dans BOTH old DB et CSV: {len(old_urls & csv_urls)}")

conn.close()

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("RÉSUMÉ DES VOLUMES")
print("=" * 70)

all_unique_urls = csv_urls
print(f"  Total URLs uniques dans checkpoint.csv: {len(all_unique_urls)}")
print(f"  Total entrées dans SQLite: {db_total}")
print(f"  Différence (CSV - DB): {len(all_unique_urls) - db_total}")
print(f"  Déficit pour 33,001: {max(0, 33001 - db_total)}")

# Breakdown of duplicates
# How many CSV rows share same URL?
csv_url_counts = Counter(r['google_maps_url'].strip() for r in rows if r.get('google_maps_url', '').strip())
multi_csv_urls = {k: v for k, v in csv_url_counts.items() if v > 1}
print(f"\n  Doublons d'URL dans CSV: {len(multi_csv_urls)} URLs (sur {len(csv_url_counts)} totales)")
print(f"  Lignes concernées par doublons URL: {sum(v - 1 for v in multi_csv_urls.values())}")

# How many CSV rows share same place_id?
csv_pid_counts = Counter(r['place_id_si_visible'].strip() for r in rows if r.get('place_id_si_visible', '').strip())
multi_csv_pids = {k: v for k, v in csv_pid_counts.items() if v > 1}
print(f"  Doublons place_id dans CSV: {len(multi_csv_pids)} (sur {len(csv_pid_counts)} totales)")
lines_doublons = sum(v - 1 for v in multi_csv_pids.values())
print(f"  Lignes concernées: {lines_doublons}")

print(f"\n  DEFICIT POUR 33 001 FICHES UNIQUE: {33001 - db_total}")
