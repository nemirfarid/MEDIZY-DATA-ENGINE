#!/usr/bin/env Python3
"""
Phase 3.2: Recover names in checkpoint from September checkpoint,
then update import_checkpoint_to_sqlite to exclude CANDIDATE entries.
"""
import csv, shutil
from pathlib import Path

CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
SEPT_CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
BACKUP = r'D:\SANTE_DZ_EXPORTS\backups\checkpoint_backup_pre_recover_20261010.csv'

ERROR_PATTERNS = [
    'impossible d', 'erreur de connexion', 'timeout', 'captcha',
    'page introuvable', 'accès refusé', 'service indisponible',
    'aucun résultat trouvé', 'aucune correspondance',
]

def is_error_artifact(name, address=''):
    text = (name + ' ' + address).lower().strip()
    for pattern in ERROR_PATTERNS:
        if pattern in text:
            return True
    return False

# Step 1: Load September checkpoint
print("Loading September checkpoint...")
with open(SEPT_CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    sept_rows = list(reader)

# Build URL → valid name mapping
url_to_sept_name = {}
for r in sept_rows:
    url = r.get('google_maps_url', '').strip()
    nom = r.get('nom', '').strip()
    if url and not is_error_artifact(nom) and len(nom) > 2:
        url_to_sept_name[url] = nom

print(f"September entries with valid names: {len(url_to_sept_name)}")

# Step 2: Read current checkpoint (already has name_status and real_name_recovered columns)
print("\nLoading current checkpoint...")
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows = list(reader)

print(f"Checkpoint rows: {len(all_rows)}")

# Step 3: Recover names for CANDIDATE entries with recoverable names
recovered = 0
for row in all_rows:
    if row.get('name_status', '') == 'CANDIDATE':
        url = row.get('google_maps_url', '').strip()
        real_name = row.get('real_name_recovered', '').strip()
        
        if url in url_to_sept_name and not real_name:
            real_name = url_to_sept_name[url]
        
        if real_name and not is_error_artifact(real_name):
            old_nom = row.get('nom', '').strip()
            row['nom'] = real_name
            row['nom_normalized'] = real_name.lower().strip() if 'nom_normalized' in fieldnames else row.get('nom_normalized', real_name.lower().strip())
            row['name_status'] = 'RECOVERED'
            row['name_source'] = 'google_maps_public_ui_2026-09'
            row['recovery_date'] = '2026-10-10'
            recovered += 1

print(f"Names recovered: {recovered}")

# Step 4: Backup before writing
shutil.copy2(CHECKPOINT, BACKUP)
print(f"Backup created: {BACKUP}")

# Step 5: Write updated checkpoint
with open(CHECKPOINT, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in all_rows:
        writer.writerow(row)

print(f"Checkpoint updated: {len(all_rows)} rows")

# Summary
candidates = sum(1 for r in all_rows if r.get('name_status', '') == 'CANDIDATE')
verified = sum(1 for r in all_rows if r.get('name_status', '') == 'VERIFIED')
recovered_count = sum(1 for r in all_rows if r.get('name_status', '') == 'RECOVERED')
print(f"  VERIFIED: {verified}")
print(f"  RECOVERED: {recovered_count}")
print(f"  CANDIDATE (excluded from DB): {candidates}")
print(f"  Total importable: {verified + recovered_count}")
