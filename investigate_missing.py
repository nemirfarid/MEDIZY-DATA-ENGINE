#!/usr/bin/env Python3
"""Investigate the 389 non-candidate entries missing from DB."""
import csv, sqlite3

CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'

# Get DB URLs and place_ids
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT google_maps_url FROM places")
db_urls = set(r[0] for r in cur.fetchall() if r[0])
cur.execute("SELECT place_id FROM places")
db_place_ids = set(r[0] for r in cur.fetchall() if r[0])
cur.execute("SELECT COUNT(*) FROM places")
db_count = cur.fetchone()[0]
conn.close()

print(f"DB entries: {db_count}")
print(f"DB URLs: {len(db_urls)}")
print(f"DB place_ids: {len(db_place_ids)}")

# Read checkpoint
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    all_rows = list(reader)

# Find non-candidate entries not in DB
missing = []
for r in all_rows:
    status = r.get('name_status', 'VERIFIED')
    if status != 'CANDIDATE':
        url = r.get('google_maps_url', '').strip()
        pid = r.get('place_id_si_visible', '').strip()
        if not url or url not in db_urls:
            missing.append(r)

print(f"\nNon-CANDIDATE entries missing from DB: {len(missing)}")

# Categorize
empty_url = [r for r in missing if not r.get('google_maps_url', '').strip()]
with_url = [r for r in missing if r.get('google_maps_url', '').strip() and r.get('google_maps_url', '').strip() not in db_urls]

print(f"  Empty URL: {len(empty_url)}")
print(f"  Has URL not in DB: {len(with_url)}")

# Check: among the 388 with URLs not in DB, are their place_ids already in DB?
pid_in_db = 0
pid_not_in_db = 0
for r in with_url:
    pid = r.get('place_id_si_visible', '').strip()
    if pid and pid in db_place_ids:
        pid_in_db += 1
    else:
        pid_not_in_db += 1

print(f"\n  Among 388: place_id already in DB (true duplicate by place_id): {pid_in_db}")
print(f"  Among 388: place_id NOT in DB (should be imported!): {pid_not_in_db}")

# These 388 entries have URLs not in DB. Why weren't they imported?
# Check if their URLs exist in DB with different format
print(f"\n=== Sample of 10 entries with URL not in DB but place_id also not in DB ===")
count_shown = 0
for r in with_url[:20]:
    pid = r.get('place_id_si_visible', '').strip()
    url = r.get('google_maps_url', '').strip()
    
    if pid and pid not in db_place_ids:
        # Check if this URL pattern exists in DB
        url_prefix = url[:50] if url else ''
        count_shown += 1
        print(f"\n  [{count_shown}] Nom: {r.get('nom', '')[:50]}")
        print(f"  Wilaya: {r.get('wilaya', '')}")
        print(f"  URL: {url[:100]}")
        print(f"  place_id: '{pid}'")
        print(f"  name_status: {r.get('name_status', '')}")
        print(f"  scrape_date: {r.get('scrape_date', '')}")
        if count_shown >= 10:
            break

# Now check: why did INSERT OR IGNORE reject these?
# The UNIQUE constraints are on place_id and google_maps_url
# Let's check if the URLs are malformed or truncated
print(f"\n=== Checking if URLs are truncated/malformed ===")
sample = with_url[:5]
for r in sample:
    url = r.get('google_maps_url', '').strip()
    print(f"  URL length: {len(url)}, ends with: ...{url[-30:] if url else 'EMPTY'}")

# Check: maybe the URL contains query params that differ
# Let's check a specific one
print(f"\n=== Spot checking one entry ===")
if with_url:
    r = with_url[0]
    url = r.get('google_maps_url', '').strip()
    print(f"  Checkpoint URL: {url[:100]}")
    # Search for similar URLs in DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT google_maps_url FROM places WHERE google_maps_url LIKE ?", (url[:40] + '%',))
    db_matches = cur.fetchall()
    if db_matches:
        print(f"  Similar URLs in DB: {len(db_matches)}")
        for m in db_matches[:3]:
            print(f"    DB: {m[0][:100]}")
    else:
        print(f"  No similar URLs in DB")
    
    # Check by place_id
    pid = r.get('place_id_si_visible', '').strip()
    if pid:
        cur.execute("SELECT nom FROM places WHERE place_id = ?", (pid,))
        pid_match = cur.fetchone()
        if pid_match:
            print(f"  Same place_id in DB, nom: {pid_match[0][:50]}")
        else:
            print(f"  place_id NOT in DB at all!")
    conn.close()
