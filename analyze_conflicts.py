#!/usr/bin/env python3
"""Analyze the 176 'more complete' conflict entries for field-level differences."""
import csv, sqlite3, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CHECKPOINT_PATH = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
OLD_DB_PATH = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_20261010_014940.db'
ENRICHMENT_PATH = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
SNAPSHOT_PATH = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
FIELDS = ['wilaya', 'commune', 'categorie_recherche', 'nom', 'adresse', 'telephone', 'site_web',
          'note', 'nombre_avis', 'horaires', 'latitude', 'longitude', 'google_maps_url',
          'place_id_si_visible', 'type_google', 'statut', 'scrape_date', 'source']

def load_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def load_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT wilaya, commune, categorie_recherche, nom, adresse, telephone, site_web,
               note, nombre_avis, horaires, CAST(latitude AS TEXT), CAST(longitude AS TEXT),
               google_maps_url, place_id, type_google, status, scrape_date, source
        FROM places
    """)
    rows = []
    for r in cursor.fetchall():
        row = dict(zip(FIELDS, r))
        for k in row:
            if row[k] is None:
                row[k] = ''
        rows.append(row)
    conn.close()
    return rows

# Load all sources
print("=== CHARGEMENT DES SOURCES ===")
ckpt = load_csv(CHECKPOINT_PATH)
old_db = load_db(OLD_DB_PATH)
enrich = load_csv(ENRICHMENT_PATH)
snap = load_csv(SNAPSHOT_PATH)

# Build pid -> row mappings
ckpt_by_pid = {r['place_id_si_visible'].strip(): r for r in ckpt if r.get('place_id_si_visible', '').strip()}
ckpt_by_url = {r['google_maps_url'].strip(): r for r in ckpt if r.get('google_maps_url', '').strip()}

def count_filled(row):
    return sum(1 for v in row.values() if v and str(v).strip())

# Load all historical entries from all 3 sources
hist_rows = enrich + snap + old_db
print(f"Total historical entries: {len(hist_rows)}")
print(f"Checkpoint entries: {len(ckpt)}")

# Build historical pid -> row mapping (take the most complete version for each pid)
hist_by_pid = {}
hist_by_url = {}
for r in hist_rows:
    pid = r.get('place_id_si_visible', '').strip()
    url = r.get('google_maps_url', '').strip()
    if pid:
        if pid not in hist_by_pid or count_filled(hist_by_pid[pid]) < count_filled(r):
            hist_by_pid[pid] = r
    if url:
        hist_by_url[url] = r

def count_filled(row):
    return sum(1 for v in row.values() if v and str(v).strip())

# Find conflicts: same pid, different URL
conflicts = []
for pid, hist_row in hist_by_pid.items():
    if pid in ckpt_by_pid:
        ckpt_row = ckpt_by_pid[pid]
        if hist_row['google_maps_url'].strip() != ckpt_row['google_maps_url'].strip():
            ckpt_score = count_filled(ckpt_row)
            hist_score = count_filled(hist_row)
            conflicts.append({
                'pid': pid,
                'ckpt_url': ckpt_row['google_maps_url'].strip(),
                'hist_url': hist_row['google_maps_url'].strip(),
                'ckpt_score': ckpt_score,
                'hist_score': hist_score,
                'ckpt_row': ckpt_row,
                'hist_row': hist_row,
            })

print(f"\n=== CONFLITS (même place_id, URL différente) ===")
print(f"Total conflits: {len(conflicts)}")

# Breakdown
more_complete = [c for c in conflicts if c['hist_score'] > c['ckpt_score']]
equal_complete = [c for c in conflicts if c['hist_score'] == c['ckpt_score']]
less_complete = [c for c in conflicts if c['hist_score'] < c['ckpt_score']]

print(f"  Plus complète (hist > ckpt): {len(more_complete)}")
print(f"  Égale: {len(equal_complete)}")
print(f"  Moins complète (hist < ckpt): {len(less_complete)}")

# For more_complete conflicts, analyze what fields differ
print("\n=== ANALYSE DES CHAMPS DIFFÉRENTS (176 cas plus complets) ===")
field_diffs = defaultdict(lambda: {'hist_has_ckpt_empty': 0, 'ckpt_has_hist_empty': 0, 'different': 0})

for c in more_complete[:20]:  # Sample first 20
    cr = c['ckpt_row']
    hr = c['hist_row']
    print(f"\n  place_id: {c['pid']}")
    print(f"  Nom: {hr.get('nom', '')}")
    print(f"  Wilaya: {hr.get('wilaya', '')}")
    print(f"  Catégorie: {hr.get('categorie_recherche', '')}")
    for field in FIELDS:
        cv = cr.get(field, '').strip()
        hv = hr.get(field, '').strip()
        if cv != hv:
            symbol = "+" if hv and not cv else ("-" if cv and not hv else "~")
            print(f"    [{symbol}] {field}: ckpt='{cv[:60]}' | hist='{hv[:60]}'")

# Aggregate field differences across ALL more_complete conflicts
for c in more_complete:
    cr = c['ckpt_row']
    hr = c['hist_row']
    for field in FIELDS:
        cv = cr.get(field, '').strip()
        hv = hr.get(field, '').strip()
        if hv and not cv:
            field_diffs[field]['hist_has_ckpt_empty'] += 1
        elif cv and not hv:
            field_diffs[field]['ckpt_has_hist_empty'] += 1
        elif cv != hv:
            field_diffs[field]['different'] += 1

print("\n=== AGGREGAT ETENDUS DES DIFFÉRENCES DE CHAMPS (176 cas) ===")
for field in FIELDS:
    d = field_diffs[field]
    total = d['hist_has_ckpt_empty'] + d['ckpt_has_hist_empty'] + d['different']
    if total > 0:
        print(f"  {field}: hist a + ckpt vide={d['hist_has_ckpt_empty']}, ckpt a + hist vide={d['ckpt_has_hist_empty']}, différent={d['different']}")

# Check if any fields are systematically missing in the checkpoint
print("\n=== CHAMPS D'INFORMATION SYSTÉMATIQUEMENT MANQUANTS ===")
for field in FIELDS:
    missing_in_ckpt = sum(1 for c in conflicts if not c['ckpt_row'].get(field, '').strip() and c['hist_row'].get(field, '').strip())
    if missing_in_ckpt > 50:
        print(f"  {field}: manquant dans ckpt pour {missing_in_ckpt}/{len(conflicts)} conflits (mais présent dans hist)")

# Also check the 1 entry without URL
print("\n=== ENTRÉE SANS URL (analyse) ===")
ckpt_urls_only = {r['google_maps_url'].strip(): r for r in ckpt if r.get('google_maps_url', '').strip()}
for r in hist_rows:
    if not r.get('google_maps_url', '').strip():
        pid = r.get('place_id_si_visible', '').strip()
        in_ckpt_by_pid = pid in ckpt_by_pid if pid else False
        print(f"  Nom: {r.get('nom', '')}")
        print(f"  Wilaya: {r.get('wilaya', '')}")
        print(f"  Catégorie: {r.get('categorie_recherche', '')}")
        print(f"  place_id: {pid}")
        print(f"  Dans ckpt par place_id: {in_ckpt_by_pid}")
        print(f"  Téléphone: {r.get('telephone', '')}")
        print(f"  GPS: {r.get('latitude', '')}, {r.get('longitude', '')}")
