#!/usr/bin/env Python3
"""
Phase 4.1: Check if checkpoint_enrichment.csv has data to enrich existing DB entries.
"""
import csv, sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ENRICHMENT = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'

# Load enrichment data
with open(ENRICHMENT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    enrich_rows = list(reader)

# Build URL→enrichment map
enrich_map = {}
for r in enrich_rows:
    url = r.get('google_maps_url', '').strip()
    if url:
        enrich_map[url] = r

print(f"Enrichment entries: {len(enrich_rows)}")
print(f"Unique URLs in enrichment: {len(enrich_map)}")

# Get DB entries
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id, nom, adresse, telephone, site_web, note, horaires, google_maps_url, wilaya FROM places")
db_rows = cur.fetchall()
conn.close()

# For each DB entry, check if enrichment has additional data
enrichable = {
    'adresse': 0,
    'telephone': 0,
    'site_web': 0,
    'note': 0,
    'horaires': 0,
}

examples = {k: [] for k in enrichable}

for db_row in db_rows:
    db_id = db_row[0]
    db_nom = db_row[1]
    db_adr = db_row[2] or ''
    db_tel = db_row[3] or ''
    db_site = db_row[4] or ''
    db_note = db_row[5] or ''
    db_horaires = db_row[6] or ''
    db_url = db_row[7] or ''
    
    enrich = enrich_map.get(db_url)
    if not enrich:
        continue
    
    # Check each field
    if not db_adr and enrich.get('adresse', '').strip():
        enrichable['adresse'] += 1
        if len(examples['adresse']) < 2:
            examples['adresse'].append((db_nom, db_url, enrich.get('adresse', '')))
    
    if not db_tel and enrich.get('telephone', '').strip():
        enrichable['telephone'] += 1
        if len(examples['telephone']) < 2:
            examples['telephone'].append((db_nom, db_url, enrich.get('telephone', '')))
    
    if not db_site and enrich.get('site_web', '').strip():
        enrichable['site_web'] += 1
        if len(examples['site_web']) < 2:
            examples['site_web'].append((db_nom, db_url, enrich.get('site_web', '')))
    
    if not db_note and enrich.get('note', '').strip():
        enrichable['note'] += 1
        if len(examples['note']) < 2:
            examples['note'].append((db_nom, db_url, enrich.get('note', '')))
    
    if not db_horaires and enrich.get('horaires', '').strip():
        enrichable['horaires'] += 1
        if len(examples['horaires']) < 2:
            examples['horaires'].append((db_nom, db_url, enrich.get('horaires', '')))

print(f"\n=== Potential enrichment from checkpoint_enrichment.csv ===")
for field, count in enrichable.items():
    print(f"  {field}: {count} entries could be enriched")
    for ex in examples[field]:
        print(f"    Example: {ex[0][:40]}, {field}={ex[2][:60]}")

# Check if any enrichment entries have URLs NOT in DB (new entries)
db_urls = set(r[7] for r in db_rows if r[7])
new_from_enrich = [r for r in enrich_rows if r.get('google_maps_url', '').strip() not in db_urls]
print(f"\nEnrichment entries with new URLs (not in DB): {len(new_from_enrich)}")

# Check if any have valid names (non-artifact)
from collections import Counter
ERROR_PATTERNS = ['impossible d', 'erreur de connexion', 'timeout', 'captcha']
def is_error_artifact(name):
    text = name.lower().strip()
    for p in ERROR_PATTERNS:
        if p in text:
            return True
    return False

valid_new = [r for r in new_from_enrich if not is_error_artifact(r.get('nom', ''))]
print(f"  Of those, valid names: {len(valid_new)}")
