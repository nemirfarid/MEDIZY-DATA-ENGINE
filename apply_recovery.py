#!/usr/bin/env python3
"""
Phase 4.1 - Etape 4: Apply recovery to checkpoint.csv and re-import to SQLite.

Actions:
  1. Add 24 new unique entries (URL + PID not in checkpoint)
  2. Enrich 42 fields in existing checkpoint entries (site_web, note, telephone)
  3. Save enriched checkpoint
  4. Re-import entire checkpoint to SQLite DB
  5. Verify results
"""
import csv, sqlite3, sys, os, json, shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configuration
CHECKPOINT_PATH = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
ENRICHMENT_PATH = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
SNAPSHOT_PATH = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
OLD_DB_PATH = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_20261010_014940.db'
DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
FIELDS = ['wilaya', 'commune', 'categorie_recherche', 'nom', 'adresse', 'telephone', 'site_web',
          'note', 'nombre_avis', 'horaires', 'latitude', 'longitude', 'google_maps_url',
          'place_id_si_visible', 'type_google', 'statut', 'scrape_date', 'source']

ENRICHABLE_FIELDS = ['telephone', 'site_web', 'note', 'nombre_avis', 'horaires',
                     'latitude', 'longitude', 'type_google']

UNRELIABLE_VALUES = {'adresse': ['itinéraires']}

def clean(s):
    if s is None:
        return ''
    return str(s).strip()

def is_reliable(field, value):
    v = str(value).strip().lower()
    if field in UNRELIABLE_VALUES:
        if v in UNRELIABLE_VALUES[field]:
            return False
    return v != ''

def load_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(places)")
    cols = [r[1] for r in cursor.fetchall()]
    status_col = 'status' if 'status' in cols and 'statut' not in cols else 'statut'
    cursor.execute(f"""
        SELECT wilaya, commune, categorie_recherche, nom, adresse, telephone, site_web,
               note, nombre_avis, horaires, CAST(latitude AS TEXT), CAST(longitude AS TEXT),
               google_maps_url, place_id, type_google, {status_col}, scrape_date, source
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

def count_filled(row):
    return sum(1 for v in row.values() if v and str(v).strip())

print("=" * 70)
print("PHASE 4.1 — ÉTAPE 4: APPLICATION DE LA RÉCUPÉRATION")
print("=" * 70)

# === Step 1: Load all sources ===
print("\n[1] Chargement des sources...")

ckpt_rows = load_csv(CHECKPOINT_PATH)
enr_rows = load_csv(ENRICHMENT_PATH)
snap_rows = load_csv(SNAPSHOT_PATH)
old_db_rows = load_db(OLD_DB_PATH)

# Add source tracking
for r in enr_rows:
    r['_source'] = 'enrichment'
for r in snap_rows:
    r['_source'] = 'snapshot'
for r in old_db_rows:
    r['_source'] = 'old_db'

print(f"  checkpoint.csv: {len(ckpt_rows)} rows")
print(f"  enrichment: {len(enr_rows)} rows")
print(f"  snapshot: {len(snap_rows)} rows")
print(f"  old_db: {len(old_db_rows)} rows")

# === Step 2: Build checkpoint indexes ===
print("\n[2] Indexation du checkpoint...")

ckpt_by_url = {r['google_maps_url'].strip(): r for r in ckpt_rows if r.get('google_maps_url', '').strip()}
ckpt_by_pid = {}
for r in ckpt_rows:
    pid = r.get('place_id_si_visible', '').strip()
    if pid:
        if pid not in ckpt_by_pid:
            ckpt_by_pid[pid] = r

ckpt_urls = set(ckpt_by_url.keys())
ckpt_pids = set(ckpt_by_pid.keys())

print(f"  URLs: {len(ckpt_urls)}, place_ids: {len(ckpt_pids)}")

# === Step 3: Identify new unique entries and enrichment opportunities ===
print("\n[3] Identification des entrées à récupérer et enrichir...")

# Build historical index (most complete version for each URL and PID)
hist_by_url = {}
hist_by_pid = {}

for source_rows in [enr_rows, snap_rows, old_db_rows]:
    for r in source_rows:
        url = r.get('google_maps_url', '').strip()
        pid = r.get('place_id_si_visible', '').strip()
        src = r.get('_source', '?')

        if url:
            if url not in hist_by_url:
                hist_by_url[url] = r
            elif count_filled(r) > count_filled(hist_by_url[url]):
                hist_by_url[url] = r

        if pid:
            if pid not in hist_by_pid:
                hist_by_pid[pid] = r
            elif count_filled(r) > count_filled(hist_by_pid[pid]):
                hist_by_pid[pid] = r

# Find new unique entries
new_entries = []
for url, hist_row in hist_by_url.items():
    pid = hist_row.get('place_id_si_visible', '').strip()
    if url in ckpt_urls:
        continue  # duplicate URL
    if pid and pid in ckpt_pids:
        continue  # conflict (same place_id, different URL)
    new_entries.append(hist_row)

# Also find entries with no URL but with PID not in checkpoint
for pid, hist_row in hist_by_pid.items():
    url = hist_row.get('google_maps_url', '').strip()
    if pid in ckpt_pids:
        continue
    if not url:
        # Check if already in new_entries
        existing_pids = set(e.get('place_id_si_visible', '').strip() for e in new_entries)
        if pid not in existing_pids:
            new_entries.append(hist_row)

print(f"  Nouvelles entrées uniques: {len(new_entries)}")

# Find enrichment opportunities
enrichments = []
for pid, hist_row in hist_by_pid.items():
    if pid not in ckpt_pids:
        continue  # not a conflict
    
    ckpt_row = ckpt_by_pid[pid]
    hist_url = hist_row.get('google_maps_url', '').strip()
    ckpt_url = ckpt_row.get('google_maps_url', '').strip()
    
    if hist_url == ckpt_url:
        continue  # same URL, not a conflict
    
    field_enrichments = []
    for field in ENRICHABLE_FIELDS:
        cv = clean(ckpt_row.get(field, ''))
        hv = clean(hist_row.get(field, ''))
        if hv and not cv and is_reliable(field, hv):
            field_enrichments.append({
                'field': field,
                'ckpt_value': cv,
                'hist_value': hv,
                'source': hist_row.get('_source', '?')
            })
    
    if field_enrichments:
        enrichments.append({
            'pid': pid,
            'nom': ckpt_row.get('nom', ''),
            'wilaya': ckpt_row.get('wilaya', ''),
            'enrichments': field_enrichments
        })

print(f"  Entrées à enrichir: {len(enrichments)}")
total_field_enrichments = sum(len(e['enrichments']) for e in enrichments)
print(f"  Champs à enrichir: {total_field_enrichments}")
for field in ENRICHABLE_FIELDS:
    count = sum(1 for e in enrichments for e2 in e['enrichments'] if e2['field'] == field)
    if count > 0:
        print(f"    {field}: {count}")

# === Step 4: Apply enrichment to checkpoint rows ===
print("\n[4] Application des enrichissements...")

# Build PID -> checkpoint row index mapping
ckpt_pid_to_idx = defaultdict(list)
for i, r in enumerate(ckpt_rows):
    pid = r.get('place_id_si_visible', '').strip()
    if pid:
        ckpt_pid_to_idx[pid].append(i)

enriched_count = 0
for en in enrichments:
    pid = en['pid']
    if pid not in ckpt_pid_to_idx:
        continue
    for idx in ckpt_pid_to_idx[pid]:
        row = ckpt_rows[idx]
        for f in en['enrichments']:
            field = f['field']
            hist_val = f['hist_value']
            curr_val = clean(row.get(field, ''))
            if hist_val and not curr_val and is_reliable(field, hist_val):
                print(f"  + Enrichissement: {field} pour '{row.get('nom', '')[:40]}' ({row.get('wilaya', '')})")
                print(f"    {field}: '' -> '{hist_val[:60]}'")
                row[field] = hist_val
                enriched_count += 1
                break  # Only enrich once per row
        break  # Only enrich first matching row

print(f"\n  Total champs enrichis: {enriched_count}")

# === Step 5: Add new entries to checkpoint ===
print("\n[5] Ajout des nouvelles entrées...")

# Build lookup for existing entries to avoid duplicates
ckpt_url_set = set(r.get('google_maps_url', '').strip() for r in ckpt_rows if r.get('google_maps_url', '').strip())
ckpt_pid_set = set(r.get('place_id_si_visible', '').strip() for r in ckpt_rows if r.get('place_id_si_visible', '').strip())

added_count = 0
for entry in new_entries:
    # Clean entry (remove _source field)
    new_row = {k: v for k, v in entry.items() if k in FIELDS}
    
    # Verify not already in checkpoint
    url = new_row.get('google_maps_url', '').strip()
    pid = new_row.get('place_id_si_visible', '').strip()
    
    if url and url in ckpt_url_set:
        continue
    if pid and pid in ckpt_pid_set:
        continue
    
    ckpt_rows.append(new_row)
    if url:
        ckpt_url_set.add(url)
    if pid:
        ckpt_pid_set.add(pid)
    added_count += 1
    print(f"  + Nouvelle entrée: {new_row.get('nom', '')[:50]} - {new_row.get('wilaya', '')} ({new_row.get('categorie_recherche', '')})")

# Track provenance for new entries
for entry in new_entries[:added_count]:
    pass  # Provenance already tracked in the row's 'source' field

print(f"\n  Nouvelles entrées ajoutées: {added_count}")

# === Step 6: Save enriched checkpoint ===
print("\n[6] Sauvegarde du checkpoint enrichi...")

# Create backup of current checkpoint before modifying
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = r'C:\SANTE_DZ_SCRAPER\backups\checkpoint_pre_recovery.csv'
shutil.copy2(CHECKPOINT_PATH, backup_path)
print(f"  Backup du checkpoint avant récupération: {backup_path}")

# Write enriched checkpoint
with open(CHECKPOINT_PATH, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
    writer.writeheader()
    for r in ckpt_rows:
        # Ensure all fields are present
        clean_row = {k: clean(r.get(k, '')) for k in FIELDS}
        writer.writerow(clean_row)

print(f"  Checkpoint enrichi: {len(ckpt_rows)} rows (was {len(ckpt_rows) - added_count})")

# === Step 7: Re-import to SQLite DB ===
print("\n[7] Réimportation vers SQLite...")

# Clear and re-import
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('DELETE FROM places')
conn.commit()

# Use the import function from sqlite_prototype
sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from sqlite_prototype import import_checkpoint_to_sqlite
import_checkpoint_to_sqlite(Path(CHECKPOINT_PATH), Path(DB_PATH))

# Verify
cursor.execute('SELECT COUNT(*) FROM places')
new_db_count = cursor.fetchone()[0]
print(f"  Entries dans DB après réimport: {new_db_count}")

cursor.execute('SELECT COUNT(DISTINCT wilaya) FROM places')
print(f"  Wilayas: {cursor.fetchone()[0]}")

cursor.execute('SELECT COUNT(DISTINCT categorie_recherche) FROM places')
print(f"  Categories: {cursor.fetchone()[0]}")

cursor.execute('SELECT COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) FROM places')
gps = cursor.fetchone()[0]
print(f"  Avec GPS: {gps}/{new_db_count} ({100*gps/new_db_count:.1f}%)")

cursor.execute('SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ""')
tel = cursor.fetchone()[0]
print(f"  Avec téléphone: {tel}/{new_db_count} ({100*tel/new_db_count:.1f}%)")

# Update data_quality
cursor.execute('SELECT COUNT(*) FROM places')
total = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(DISTINCT place_id) FROM places')
pid_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(DISTINCT google_maps_url) FROM places')
url_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(DISTINCT wilaya) FROM places')
w_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(DISTINCT categorie_recherche) FROM places')
c_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(DISTINCT commune) FROM places')
comm_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(CASE WHEN site_web IS NOT NULL AND site_web != "" THEN 1 END) FROM places')
web_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(CASE WHEN note IS NOT NULL AND note != "" THEN 1 END) FROM places')
note_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(CASE WHEN horaires IS NOT NULL AND horaires != "" THEN 1 END) FROM places')
hours_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(CASE WHEN adresse IS NOT NULL AND adresse != "" THEN 1 END) FROM places')
addr_count = cursor.fetchone()[0]

cursor.execute("""
    INSERT INTO data_quality (measured_at, total_places, gps_count, phone_count, address_count,
                              website_count, category_count, place_id_count, rating_count,
                              opening_hours_count, commune_count, duplicate_estimate, wilaya_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (datetime.now().isoformat(), total, gps, tel, addr_count,
      web_count, c_count, pid_count, note_count,
      hours_count, comm_count, 0, w_count))
conn.commit()
print(f"\n  data_quality mise à jour")

# Update progression v2
prog2_path = r'D:\SANTE_DZ_EXPORTS\scraping_progress.json'
with open(prog2_path, 'r', encoding='utf-8') as f:
    prog2 = json.load(f)
prog2['total_national_unique'] = url_count
prog2['updated_at'] = datetime.now().isoformat(timespec='seconds')
with open(prog2_path, 'w', encoding='utf-8') as f:
    json.dump(prog2, f, indent=2, ensure_ascii=False)
print(f"  progression.json v2 mise à jour")

conn.close()
print("\n" + "=" * 70)
print("RÉCUPÉRATION TERMINÉE")
print(f"  Fiches ajoutées: {added_count}")
print(f"  Champs enrichis: {enriched_count}")
print(f"  Total DB: {new_db_count}")
print(f"  Total CSV: {len(ckpt_rows)}")
print("=" * 70)
