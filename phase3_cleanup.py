#!/usr/bin/env Python3
"""
Phase 3.1: Clean checkpoint — recover names from September checkpoint where possible,
flag remaining error artifacts as CANDIDATE (preserve data, don't import to DB with fake names).
"""
import csv, shutil, json, sqlite3
from datetime import datetime
from collections import Counter

CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
BACKUP = r'D:\SANTE_DZ_EXPORTS\backups\checkpoint_backup_pre_clean_20261010.csv'
DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
PROGRESSION = r'D:\SANTE_DZ_EXPORTS\scraping_progress.json'
SEPT_CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'

# Error artifact keywords (case-insensitive)
ERROR_PATTERNS = [
    'impossible d',
    'erreur de connexion',
    'timeout',
    'captcha',
    'page introuvable',
    'accès refusé',
    'service indisponible',
    'aucun résultat trouvé',
    'aucune correspondance',
]

def is_error_artifact(name, address=''):
    text = (name + ' ' + address).lower().strip()
    for pattern in ERROR_PATTERNS:
        if pattern in text:
            return True
    return False

# Step 1: Load September checkpoint to build URL→name mapping
print("Loading September checkpoint...")
with open(SEPT_CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    sept_fieldnames = reader.fieldnames
    sept_rows = list(reader)

print(f"September rows: {len(sept_rows)}")
print(f"September columns: {sept_fieldnames}")

# Build URL → name mapping (for entries with valid names)
url_to_sept = {}
for r in sept_rows:
    url = r.get('google_maps_url', '').strip()
    nom = r.get('nom', '').strip()
    if url and not is_error_artifact(nom):
        url_to_sept[url] = r

print(f"September entries with valid names: {len(url_to_sept)}")

# Step 2: Read current checkpoint
print("\nLoading current checkpoint...")
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows = list(reader)

print(f"Current checkpoint rows: {len(all_rows)}")

# Step 3: Identify error artifacts and attempt name recovery
artifacts = []
recovered = 0
not_recovered = 0

for row in all_rows:
    nom = row.get('nom', '').strip()
    adr = row.get('adresse', '').strip()
    
    if is_error_artifact(nom, adr):
        artifacts.append(row)
        url = row.get('google_maps_url', '').strip()
        
        # Note: We do NOT modify the row's nom — we flag it
        # But we check if September has the real name
        if url in url_to_sept:
            sept_row = url_to_sept[url]
            real_name = sept_row.get('nom', '').strip()
            if real_name:
                recovered += 1
        else:
            not_recovered += 1
    # Non-artifacts stay as-is

print(f"\n=== Recovery analysis ===")
print(f"Error artifacts: {len(artifacts)}")
print(f"Recoverable from September: {recovered}")
print(f"Not recoverable: {not_recovered}")

# Step 4: Backup checkpoint
shutil.copy2(CHECKPOINT, BACKUP)
print(f"Backup created: {BACKUP}")

# Step 5: Write updated checkpoint with name_status column
# For error artifacts: name_status = "CANDIDATE" (preserve all data, real name uncertain)
# For valid entries: name_status = "VERIFIED"
# We also add 'real_name_recovered' column to note if September had the real name
new_fieldnames = list(fieldnames) + ['name_status', 'real_name_recovered']

with open(CHECKPOINT, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=new_fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in all_rows:
        nom = row.get('nom', '').strip()
        adr = row.get('adresse', '').strip()
        
        if is_error_artifact(nom, adr):
            url = row.get('google_maps_url', '').strip()
            row['name_status'] = 'CANDIDATE'
            if url in url_to_sept:
                row['real_name_recovered'] = url_to_sept[url].get('nom', '').strip()
            else:
                row['real_name_recovered'] = ''
        else:
            row['name_status'] = 'VERIFIED'
            row['real_name_recovered'] = ''
        
        writer.writerow(row)

print(f"Checkpoint updated with name_status and real_name_recovered columns")

# Step 6: Report on artifacts by wilaya
wilaya_artifacts = Counter(r.get('wilaya', 'INCONNU') for r in artifacts)
print(f"\n=== Artéfacts d'erreur par wilaya (top 15) ===")
for wilaya, count in wilaya_artifacts.most_common(15):
    print(f"  {wilaya}: {count}")

# Step 7: Report on DB
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM places")
db_count = cursor.fetchone()[0]
print(f"\n=== Base de données ===")
print(f"Entrées dans DB: {db_count}")

# Check DB for artifacts
cursor.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%' OR nom LIKE '%timeout%'")
db_artifacts = cursor.fetchone()[0]
print(f"Artéfacts d'erreur dans DB: {db_artifacts}")

conn.close()

# Step 8: Summary
valid_count = len(all_rows) - len(artifacts)
print(f"\n=== RÉSUMÉ ===")
print(f"Total entrées checkpoint: {len(all_rows)}")
print(f"Entrées valides (nom correct): {valid_count}")
print(f"Artéfacts d'erreur (nom incorrect, conservés comme CANDIDATE): {len(artifacts)}")
print(f"  - Dont {recovered} récupérables via September checkpoint")
print(f"  - {not_recovered} non récupérables")
print(f"DB actuelle: {db_count} entrées (0 artéfacts attendus dans DB si précédente import était propre)")
