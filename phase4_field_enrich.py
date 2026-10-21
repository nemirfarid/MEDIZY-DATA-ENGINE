#!/usr/bin/env Python3
"""
Phase 4.3: Field-level enrichment — update existing DB entries with
missing site_web and note data from checkpoint_enrichment.csv.
Skip 'Itinéraires' adresse artifacts.
"""
import csv, sqlite3, sys, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ENRICHMENT = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
DB_BACKUP = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_field_enrich.db'

ERROR_PATTERNS = ['impossible d', 'erreur de connexion', 'timeout', 'captcha',
                   'page introuvable', 'accès refusé', 'service indisponible']
ARTIFACT_VALUES = ['itinéraires', 'itineraires', '']

def is_artifact_value(val):
    if not val:
        return True
    v = val.lower().strip()
    for a in ARTIFACT_VALUES:
        if a in v:
            return True
    return False

def is_error_artifact(name):
    text = name.lower().strip()
    for p in ERROR_PATTERNS:
        if p in text:
            return True
    return False

# Load enrichment data
with open(ENRICHMENT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    enrich_rows = list(reader)

# Build URL → enrichment map
enrich_map = {}
for r in enrich_rows:
    url = r.get('google_maps_url', '').strip()
    if url:
        enrich_map[url] = r

# Get DB entries
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id, google_maps_url, nom, site_web, note FROM places")
db_rows = cur.fetchall()

# Find entries that can be enriched (field empty in DB but filled in enrichment)
updates = {
    'site_web': [],
    'note': [],
    'adresse': [],
}

for db_id, db_url, db_nom, db_site, db_note in db_rows:
    if not db_url:
        continue
    
    enrich = enrich_map.get(db_url)
    if not enrich:
        continue
    
    # site_web
    if (not db_site or db_site == '') and not is_artifact_value(enrich.get('site_web', '')):
        updates['site_web'].append((enrich.get('site_web', '').strip(), db_id))
    
    # note
    if (not db_note or db_note == '') and enrich.get('note', '').strip() and not is_error_artifact(enrich.get('note', '')):
        updates['note'].append((enrich.get('note', '').strip(), db_id))
    
    # adresse (skip "Itinéraires" artifacts)
    if not is_artifact_value(enrich.get('adresse', '')):
        if not db_url:  # We don't track adresse from DB here, skip
            pass

print(f"=== Field-level enrichment candidates ===")
for field, ents in updates.items():
    print(f"  {field}: {len(ents)} entries")

# Apply updates
shutil.copy2(DB_PATH, DB_BACKUP)
print(f"\nBackup created: {DB_BACKUP}")

cur.execute("SELECT COUNT(*) FROM places")
before = cur.fetchone()[0]
print(f"DB before: {before}")

total_updated = 0
for field, ents in updates.items():
    for new_val, db_id in ents:
        if field == 'site_web':
            cur.execute("UPDATE places SET site_web = ? WHERE id = ?", (new_val, db_id))
        elif field == 'note':
            cur.execute("UPDATE places SET note = ? WHERE id = ?", (new_val, db_id))
        total_updated += 1
    conn.commit()

cur.execute("SELECT COUNT(*) FROM places")
after = cur.fetchone()[0]
print(f"DB after: {after}")
print(f"Total fields updated: {total_updated}")

# Verify no new artifacts
cur.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%'")
artifacts = cur.fetchone()[0]
print(f"Error artifacts in DB: {artifacts}")

conn.close()
