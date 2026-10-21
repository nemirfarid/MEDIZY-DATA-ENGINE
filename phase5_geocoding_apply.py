#!/usr/bin/env Python3
"""
Phase 5 — Étape 2: Applique le géocodage inverse aux entrées à HAUTE confiance (< 5km).
Stocke les entrées à MEDIUM/LOW confiance dans un fichier de revue.

Principe:
- Seulement HIGH confidence (dist < 5km) est appliqué à la DB
- Source enregistrée: "geocoding_centroid_officiel_v1"
- Date et niveau de confiance enregistrés
- Aucune commune existante n'est écrasée (actuellement 0 dans DB)
- Transaction SQLite pour rollback possible
- Backup avant modification
"""
import sqlite3, json, sys, math, shutil, csv
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
DB_BACKUP = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_geocoding.db'
REVIEW_FILE = r'D:\SANTE_DZ_EXPORTS\geocoding_review_pending.csv'
APPLIED_FILE = r'D:\SANTE_DZ_EXPORTS\geocoding_applied.csv'

ALGERIA_LAT_MIN, ALGERIA_LAT_MAX = 19.5, 37.5
ALGERIA_LNG_MIN, ALGERIA_LNG_MAX = -8.5, 12.0
HIGH_CONFIDENCE_KM = 5.0
MEDIUM_CONFIDENCE_KM = 15.0

sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from communes_officielles import get_all_communes
from communes_algerie import WILAYAS

# Load communes with GPS
all_communes = get_all_communes()
communes_with_gps = [c for c in all_communes if c.get('latitude') and c.get('longitude')]
communes_by_wilaya = {}
for c in communes_with_gps:
    communes_by_wilaya.setdefault(c.get('wilaya_code', ''), []).append(c)

# Build wilaya name -> code mapping
wilaya_name_to_code = {}
for w in WILAYAS:
    name = (w.get('nom') or '').lower()
    code = w.get('code')
    if name and code:
        wilaya_name_to_code[name] = code

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# Backup DB
shutil.copy2(DB_PATH, DB_BACKUP)
print(f"Backup créé: {DB_BACKUP}")

# Read DB entries
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT id, nom, latitude, longitude, wilaya, adresse
    FROM places 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
      AND latitude BETWEEN ? AND ?
      AND longitude BETWEEN ? AND ?
      AND (commune IS NULL OR commune = '')
""", (ALGERIA_LAT_MIN, ALGERIA_LAT_MAX, ALGERIA_LNG_MIN, ALGERIA_LNG_MAX))

entries = cur.fetchall()
print(f"Entrées à géocoder: {len(entries)}")

# Compute nearest commune for each
results = {
    'high': [],
    'medium': [],
    'low': [],
}

for row in entries:
    lat, lng = row['latitude'], row['longitude']
    wilaya = row['wilaya']
    wilaya_lower = (wilaya or '').lower()
    wcode = wilaya_name_to_code.get(wilaya_lower)
    
    if not wcode:
        continue
    
    wcommunes = communes_by_wilaya.get(wcode, [])
    if not wcommunes:
        continue
    
    best_dist = float('inf')
    best_commune = None
    for c in wcommunes:
        dist = haversine(lat, lng, c['latitude'], c['longitude'])
        if dist < best_dist:
            best_dist = dist
            best_commune = c
    
    if best_commune:
        if best_dist < HIGH_CONFIDENCE_KM:
            results['high'].append((row, best_commune, best_dist))
        elif best_dist < MEDIUM_CONFIDENCE_KM:
            results['medium'].append((row, best_commune, best_dist))
        else:
            results['low'].append((row, best_commune, best_dist))

print(f"\nClassification:")
print(f"  HIGH (< {HIGH_CONFIDENCE_KM}km): {len(results['high'])}")
print(f"  MEDIUM ({HIGH_CONFIDENCE_KM}-{MEDIUM_CONFIDENCE_KM}km): {len(results['medium'])}")
print(f"  LOW (> {MEDIUM_CONFIDENCE_KM}km): {len(results['low'])}")

# Apply HIGH confidence to DB using transaction
print(f"\n=== Application des communes à HAUTE confiance ===")
timestamp = datetime.now().isoformat()
source_label = f"geocoding_centroid_officiel_v1_{timestamp[:10]}"

try:
    # Check if commune column exists
    cur.execute("PRAGMA table_info(places)")
    columns = [r[1] for r in cur.fetchall()]
    print(f"Existing columns: {columns}")
    
    # Check if commune_source and commune_confidence columns exist
    has_commune_source = 'commune_source' in columns
    has_commune_confidence = 'commune_confidence' in columns
    has_commune_updated = 'commune_updated_at' in columns
    
    if not has_commune_source:
        cur.execute("ALTER TABLE places ADD COLUMN commune_source TEXT")
    if not has_commune_confidence:
        cur.execute("ALTER TABLE places ADD COLUMN commune_confidence REAL")
    if not has_commune_updated:
        cur.execute("ALTER TABLE places ADD COLUMN commune_updated_at TEXT")
    
    # Update HIGH confidence entries
    applied_count = 0
    applied_rows = []
    for row, commune, dist in results['high']:
        cur.execute("""
            UPDATE places 
            SET commune = ?, commune_source = ?, commune_confidence = ?, commune_updated_at = ?
            WHERE id = ?
        """, (
            commune['nom_fr'],
            source_label,
            dist,
            timestamp,
            row['id'],
        ))
        applied_count += 1
        applied_rows.append({
            'id': row['id'],
            'nom': row['nom'][:60],
            'wilaya': row['wilaya'],
            'gps': f"{row['latitude']:.6f}, {row['longitude']:.6f}",
            'commune': commune['nom_fr'],
            'daira': commune.get('daira', ''),
            'distance_km': round(dist, 2),
            'confidence': 'HIGH',
        })
    
    conn.commit()
    print(f"Communes appliquées: {applied_count}")
    
    # Verify
    cur.execute("SELECT COUNT(*) FROM places WHERE commune IS NOT NULL AND commune != ''")
    with_commune = cur.fetchone()[0]
    print(f"Total entrées avec commune dans DB: {with_commune}")

except Exception as e:
    conn.rollback()
    print(f"ERREUR - transaction annulée: {e}")
    raise

# Write applied file
with open(APPLIED_FILE, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['id', 'nom', 'wilaya', 'gps', 'commune', 'daira', 'distance_km', 'confidence'])
    writer.writeheader()
    writer.writerows(applied_rows[:100])  # Save sample
print(f"Fichier des entrées appliquées (échantillon): {APPLIED_FILE}")

# Write review file for MEDIUM and LOW
review_rows = []
for tier, label in [('medium', 'MEDIUM'), ('low', 'LOW')]:
    for row, commune, dist in results[tier]:
        review_rows.append({
            'id': row['id'],
            'nom': row['nom'][:80],
            'wilaya': row['wilaya'],
            'gps': f"{row['latitude']:.6f}, {row['longitude']:.6f}",
            'assigned_commune': commune['nom_fr'],
            'daira': commune.get('daira', ''),
            'distance_km': round(dist, 2),
            'confidence_tier': label,
            'wilaya_officielle': commune.get('nom_fr', ''),
        })

with open(REVIEW_FILE, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['id', 'nom', 'wilaya', 'gps', 'assigned_commune', 'daira', 'distance_km', 'confidence_tier', 'wilaya_officielle'])
    writer.writeheader()
    writer.writerows(review_rows)
print(f"Fichier de revue (MEDIUM + LOW): {REVIEW_FILE} ({len(review_rows)} entrées)")

conn.close()

# Summary
print(f"\n=== RÉSUMÉ GÉOCODAGE ===")
print(f"  Entrées traitées: {len(entries)}")
print(f"  HIGH confidence appliquées: {len(results['high'])}")
print(f"  MEDIUM confiance (à revoir): {len(results['medium'])}")
print(f"  LOW confiance (à revoir): {len(results['low'])}")
print(f"  Total en attente de vérification: {len(review_rows)}")
print(f"  Source enregistrée: {source_label}")
print(f"  Backup: {DB_BACKUP}")
