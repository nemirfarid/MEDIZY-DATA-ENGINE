#!/usr/bin/env Python3
"""
Phase 5 — Étape 2: Géocodage inverse test sur un échantillon contrôlé.
NE MODIFIE AUCUNE DONNÉE — analyse en lecture seule.
"""
import sqlite3, json, sys, math
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
ALGERIA_LAT_MIN, ALGERIA_LAT_MAX = 19.5, 37.5
ALGERIA_LNG_MIN, ALGERIA_LNG_MAX = -8.5, 12.0

sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from communes_officielles import get_all_communes
from communes_algerie import WILAYAS

# Load communes with GPS
all_communes = get_all_communes()
communes_with_gps = [c for c in all_communes if c.get('latitude') and c.get('longitude')]
print(f"Communes officielles totales: {len(all_communes)}")
print(f"Communes avec GPS: {len(communes_with_gps)}")

# Group by wilaya code
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

# Get DB entries with valid GPS in Algeria
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

sample = cur.fetchall()
total_sample = len(sample)
print(f"\nEntrées avec GPS valide (Algerie) et commune vide: {total_sample}")

# Process
results = []
confident = 0
medium = 0
low = 0

for row in sample:
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
        confidence = 'high' if best_dist < 5.0 else ('medium' if best_dist < 15.0 else 'low')
        if confidence == 'high':
            confident += 1
        elif confidence == 'medium':
            medium += 1
        else:
            low += 1
        
        results.append({
            'id': row['id'],
            'nom': row['nom'][:50],
            'wilaya': wilaya,
            'gps': f"{lat:.6f}, {lng:.6f}",
            'matched_commune': best_commune['nom_fr'],
            'distance_km': round(best_dist, 2),
            'confidence': confidence,
        })

conn.close()

# Summary
assigned = len(results)
print(f"\n=== Résultats du géocodage ({assigned} assignées sur {total_sample}) ===")
print(f"  Haute confiance (< 5km): {confident}")
print(f"  Moyenne confiance (5-15km): {medium}")
print(f"  Faible confiance (> 15km): {low}")

# Distance distribution
dists = [r['distance_km'] for r in results]
print(f"\nDistribution des distances:")
print(f"  < 1km:  {sum(1 for d in dists if d < 1)}")
print(f"  1-3km:  {sum(1 for d in dists if 1 <= d < 3)}")
print(f"  3-5km:  {sum(1 for d in dists if 3 <= d < 5)}")
print(f"  5-10km: {sum(1 for d in dists if 5 <= d < 10)}")
print(f"  10-15km: {sum(1 for d in dists if 10 <= d < 15)}")
print(f"  > 15km: {sum(1 for d in dists if d >= 15)}")

# Wilaya coverage
wilaya_dist = {}
for r in results:
    w = r['wilaya']
    wilaya_dist.setdefault(w, {'total': 0, 'high': 0, 'medium': 0, 'low': 0})
    wilaya_dist[w]['total'] += 1
    wilaya_dist[w][r['confidence']] += 1

print(f"\n=== Couverture par wilaya (top 15) ===")
for w in sorted(wilaya_dist.keys(), key=lambda x: wilaya_dist[x]['total'], reverse=True)[:15]:
    d = wilaya_dist[w]
    print(f"  {w}: total={d['total']}, high={d['high']}, medium={d['medium']}, low={d['low']}")

# Show sample
print(f"\n=== Échantillon (high confidence) ===")
for r in [x for x in results if x['confidence'] == 'high'][:5]:
    print(f"  {r['nom'][:35]} ({r['wilaya']}): {r['matched_commune']} — {r['distance_km']}km")

print(f"\n=== Échantillon (low confidence - needs manual review) ===")
for r in [x for x in results if x['confidence'] == 'low'][:5]:
    print(f"  {r['nom'][:35]} ({r['wilaya']}): {r['matched_commune']} — {r['distance_km']}km")

# Save analysis
results_path = Path(r'D:\SANTE_DZ_EXPORTS\geocoding_analysis.json')
with open(results_path, 'w', encoding='utf-8') as f:
    json.dump({
        'total_entries_with_gps': total_sample,
        'entries_assigned': assigned,
        'high_confidence': confident,
        'medium_confidence': medium,
        'low_confidence': low,
        'confidence_threshold_km': {'high': 5.0, 'medium': 15.0},
        'wilaya_coverage': wilaya_dist,
        'sample_high_confidence': [r for r in results if r['confidence'] == 'high'][:50],
        'sample_low_confidence': [r for r in results if r['confidence'] == 'low'][:50],
    }, f, indent=2, ensure_ascii=False, default=str)
print(f"\nRapport sauvegardé: {results_path}")

print(f"\n=== CONCLUSION ===")
pct = confident / assigned * 100 if assigned > 0 else 0
print(f"Taux de confiance élevée: {pct:.1f}% des {assigned} assignées")
if pct > 70:
    print(f"-> APPROUVÉ: géocodage centroid-based avec seuil HIGH (< 5km) sur les {confident} premières entrées")
    print(f"  Les {medium + low} restantes seront placées en attente de vérification manuelle")
else:
    print(f"-> ATTENTION: seuil de confiance insuffisant, nécessite approche polygonale")
