#!/usr/bin/env Python3
"""Generate geocoding CSV files from current DB state."""
import sqlite3, csv, sys, json, math
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
SEPT_CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
APPLIED_FILE = r'D:\SANTE_DZ_EXPORTS\geocoding_applied.csv'
REVIEW_FILE = r'D:\SANTE_DZ_EXPORTS\geocoding_review_pending.csv'

ALGERIA_LAT_MIN, ALGERIA_LAT_MAX = 19.5, 37.5
ALGERIA_LNG_MIN, ALGERIA_LNG_MAX = -8.5, 12.0
HIGH_KM = 5.0
MED_KM = 15.0

sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from communes_officielles import get_all_communes
from communes_algerie import WILAYAS

# Load communes
all_communes = get_all_communes()
communes_with_gps = [c for c in all_communes if c.get('latitude') and c.get('longitude')]
communes_by_wilaya = {}
for c in communes_with_gps:
    communes_by_wilaya.setdefault(c.get('wilaya_code', ''), []).append(c)

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

# Get DB entries with GPS in Algeria
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT id, nom, latitude, longitude, wilaya, adresse, commune, commune_source, commune_confidence
    FROM places 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
      AND latitude BETWEEN ? AND ?
      AND longitude BETWEEN ? AND ?
""", (ALGERIA_LAT_MIN, ALGERIA_LAT_MAX, ALGERIA_LNG_MIN, ALGERIA_LNG_MAX))

entries = cur.fetchall()

# Find entries without commune and compute nearest commune
entries_without_commune = [r for r in entries if not r['commune']]
entries_with_commune = [r for r in entries if r['commune']]

print(f"Total entries with GPS in Algeria: {len(entries)}")
print(f"Already have commune: {len(entries_with_commune)}")
print(f"Need geocoding: {len(entries_without_commune)}")

# Compute for entries without commune
high_results = []
medium_results = []
low_results = []

for row in entries_without_commune:
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
        if best_dist < HIGH_KM:
            high_results.append((row, best_commune, best_dist))
        elif best_dist < MED_KM:
            medium_results.append((row, best_commune, best_dist))
        else:
            low_results.append((row, best_commune, best_dist))

# Note: HIGH results are already applied to DB
# Write applied CSV (all entries that now have commune from geocoding)
applied_rows = []
for row in entries_with_commune:
    if row['commune_source'] and 'geocoding' in row['commune_source']:
        applied_rows.append({
            'id': row['id'],
            'nom': row['nom'][:60] if row['nom'] else '',
            'wilaya': row['wilaya'] or '',
            'gps': f"{row['latitude']:.6f}, {row['longitude']:.6f}" if row['latitude'] else '',
            'commune': row['commune'] or '',
            'distance_km': round(row['commune_confidence'], 2) if row['commune_confidence'] else '',
            'confidence': 'HIGH',
        })

with open(APPLIED_FILE, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['id', 'nom', 'wilaya', 'gps', 'commune', 'distance_km', 'confidence'])
    writer.writeheader()
    writer.writerows(applied_rows)
print(f"\nApplied CSV written: {APPLIED_FILE} ({len(applied_rows)} rows)")

# Write review CSV
review_rows = []
for tier, label in [('medium', 'MEDIUM'), ('low', 'LOW')]:
    for row, commune, dist in medium_results if tier == 'medium' else low_results:
        review_rows.append({
            'id': row['id'],
            'nom': row['nom'][:80] if row['nom'] else '',
            'wilaya': row['wilaya'] or '',
            'gps': f"{row['latitude']:.6f}, {row['longitude']:.6f}" if row['latitude'] else '',
            'assigned_commune': commune['nom_fr'],
            'daira': commune.get('daira', ''),
            'distance_km': round(dist, 2),
            'confidence_tier': label,
        })

with open(REVIEW_FILE, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['id', 'nom', 'wilaya', 'gps', 'assigned_commune', 'daira', 'distance_km', 'confidence_tier'])
    writer.writeheader()
    writer.writerows(review_rows)
print(f"Review CSV written: {REVIEW_FILE} ({len(review_rows)} rows)")

print(f"\n=== GÉOCODAGE — RÉSUMÉ ===")
print(f"  HIGH confidence appliquées: {len(applied_rows)} (already in DB)")
print(f"  MEDIUM confiance (à revoir): {len(medium_results)}")
print(f"  LOW confiance (à revoir): {len(low_results)}")
print(f"  Total en attente: {len(review_rows)}")

conn.close()
