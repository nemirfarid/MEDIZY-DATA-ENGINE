import sqlite3
import csv
from collections import defaultdict

# ========== CONFIGURATION ==========
TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db'
GEO_CSV = r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv'

def safe(s):
    if s is None:
        return 'NULL'
    return str(s).encode('ascii', 'replace').decode()

# ========== LOAD GEOALGERIA CSV METADATA ==========
print("=" * 80)
print("CHARGEMENT MÉTADONNÉES GEOALGERIA")
print("=" * 80)

geo_meta = {}
with open(GEO_CSV, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        geo_meta[row['id']] = {
            'name_fr': row['name_fr'] or '',
            'name_ar': row['name_ar'] or '',
            'wilaya_code': row['wilaya_code'],
            'commune_code': row['commune_code'],
            'commune': row['commune'] or '',
            'geo_precision': row['geo_precision'] or '',
            'geo_method': row['geo_method'] or '',
            'source': row['source'] or '',
            'refs': row['refs'] or '',
            'type': row['type'],
            'type_label_fr': row['type_label_fr'] or '',
            'review_status': row['review_status'] or '',
            'reviewed_at': row['reviewed_at'] or '',
            'reviewed_by': row['reviewed_by'] or '',
        }

print("Entrées GeoAlgeria chargées: {}".format(len(geo_meta)))

# ========== LOAD TEST DB ENTRIES ==========
conn = sqlite3.connect(TEST_DB)
c = conn.cursor()
c.execute('''
    SELECT place_id, nom, wilaya, commune, categorie_recherche,
           latitude, longitude, source
    FROM places WHERE source LIKE "geoalgeria:%" ORDER BY place_id
''')
test_entries = c.fetchall()

print("Entrées geoalgeria dans test DB: {}".format(len(test_entries)))

# Build lookup
entries_by_pid = {}
for row in test_entries:
    pid, nom, wilaya, commune, cat, lat, lng, source = row
    entries_by_pid[pid] = {
        'place_id': pid, 'nom_fr': nom, 'wilaya': wilaya, 'commune': commune,
        'cat': cat, 'lat': lat, 'lng': lng, 'source': source
    }

# ========== MATCH WITH CSV METADATA ==========
matched = []
unmatched = []

for pid, entry in entries_by_pid.items():
    # Find matching geo_id by name/coords
    found = False
    for geo_id, meta in geo_meta.items():
        # Match by coordinates (most reliable)
        if meta['geo_precision'] in ('exact', 'approximate', 'inconnu'):
            if entry['lat'] and entry['lng']:
                try:
                    geo_lat = float(meta.get('lat', 0)) if meta.get('lat') else None
                    geo_lng = float(meta.get('lng', 0)) if meta.get('lng') else None
                except:
                    geo_lat, geo_lng = None, None
                
                # Check if lat/lng match (within small tolerance)
                if geo_lat and geo_lng:
                    if abs(entry['lat'] - geo_lat) < 0.0001 and abs(entry['lng'] - geo_lng) < 0.0001:
                        matched.append({**entry, **meta, 'geo_id': geo_id})
                        found = True
                        break
        
        # Fallback: match by name
        if not found:
            if entry['nom_fr'] and meta['name_fr']:
                if entry['nom_fr'].strip() == meta['name_fr'].strip():
                    matched.append({**entry, **meta, 'geo_id': geo_id})
                    found = True
                    break
    
    if not found:
        unmatched.append(entry)

print("Correspondances trouvées: {}".format(len(matched)))
print("Non correspondues: {}".format(len(unmatched)))

# For unmatched, try to find by name similarity
if unmatched:
    print("\nTentative de correspondance par nom pour les non-correspondus...")
    for entry in unmatched:
        for geo_id, meta in geo_meta.items():
            if entry['nom_fr'] and meta['name_fr']:
                # Simple substring check
                if entry['nom_fr'] in meta['name_fr'] or meta['name_fr'] in entry['nom_fr']:
                    matched.append({**entry, **meta, 'geo_id': geo_id})
                    break

print("Total après correspondance: {}".format(len(matched)))

# ========== GROUP 1: 6 GROUPES DE COORDONNÉES IDENTIQUES ==========
print("\n" + "=" * 80)
print("1. SIX GROUPES DE COORDONNÉES IDENTIQUES (DÉTAIL)")
print("=" * 80)

coord_groups = defaultdict(list)
for m in matched:
    lat, lng = m['lat'], m['lng']
    coord_key = (round(lat, 6), round(lng, 6))
    coord_groups[coord_key].append(m)

groups_6 = {k: v for k, v in coord_groups.items() if len(v) > 1}
print("Groupes trouvés: {}".format(len(groups_6)))

for i, (coord, entries) in enumerate(sorted(groups_6.items()), 1):
    lat, lng = coord
    print("\n--- GROUPE {} --- GPS: ({}, {}) --- {} entrées".format(i, lat, lng, len(entries)))
    for e in entries:
        name_fr = e.get('name_fr') or e.get('nom_fr') or ''
        name_ar = e.get('name_ar') or ''
        wilaya = e['wilaya']
        commune = e['commune']
        cat = e['cat']
        precision = e.get('geo_precision', '')
        method = e.get('geo_method', '')
        geo_id = e.get('geo_id', '')
        print("  place_id={} | geo_id={}".format(e['place_id'], geo_id))
        print("    FR: {}".format(safe(name_fr)))
        print("    AR: {}".format(safe(name_ar)))
        print("    Wilaya: {} | Commune: {} | Cat: {}".format(wilaya, safe(commune), cat))
        print("    Précision: {} | Méthode: {}".format(precision, method))

# ========== ANALYZE EACH GROUP FOR CO-LOCATION VS DUPLICATE ==========
print("\n" + "=" * 80)
print("2. ANALYSE CO-LOCALISATION vs DOUBLON")
print("=" * 80)

for coord, entries in sorted(groups_6.items()):
    lat, lng = coord
    print("\n--- GPS: ({}, {}) ---".format(lat, lng))
    
    # Check categories
    cats = set(e['cat'] for e in entries)
    wilayas = set(e['wilaya'] for e in entries)
    communes = set(e['commune'] for e in entries)
    geo_ids = set(e.get('geo_id', '') for e in entries)
    
    print("  Catégories: {}".format(cats))
    print("  Wilayas: {}".format(wilayas))
    print("  Communes: {}".format(communes))
    print("  GeoIDs: {}".format(geo_ids))
    
    # Determine if same establishment or co-located
    if len(cats) == 1 and len(wilayas) == 1 and len(communes) == 1:
        # Same category, same location - likely duplicate
        names = [e.get('name_fr') or e.get('nom_fr') or '' for e in entries]
        # Check name similarity
        if all(n == names[0] for n in names):
            print("  >>> DOUBLON PROBABLE (même nom, même cat, même lieu)")
        else:
            print("  >>> DOUBLON PROBABLE (même cat, même lieu, noms proches)")
    else:
        print("  >>> CO-LOCALISATION PROBABLE (catégories ou communes différentes)")
        for e in entries:
            name_fr = e.get('name_fr') or e.get('nom_fr') or ''
            name_ar = e.get('name_ar') or ''
            print("    - {} | {} | {} | {}".format(e['place_id'], safe(name_fr), e['cat'], e['commune']))

# ========== GROUP 2: 4 ENTREES SANS NOM FRANÇAIS ==========
print("\n" + "=" * 80)
print("3. QUATRE ENTRÉES SANS NOM FRANÇAIS")
print("=" * 80)

no_fr_name = []
for m in matched:
    name_fr = m.get('name_fr') or m.get('nom_fr') or ''
    if not name_fr or name_fr.strip() == '':
        no_fr_name.append(m)

print("Entrées sans nom français: {}".format(len(no_fr_name)))
for e in no_fr_name:
    name_ar = e.get('name_ar') or ''
    geo_id = e.get('geo_id', '')
    print("\n  place_id={} | geo_id={}".format(e['place_id'], geo_id))
    print("    Nom arabe: {}".format(safe(name_ar)))
    print("    Wilaya: {} | Commune: {}".format(e['wilaya'], safe(e['commune'])))
    print("    Cat: {} | GPS: ({}, {})".format(e['cat'], e['lat'], e['lng']))
    print("    Précision: {} | Méthode: {}".format(
        e.get('geo_precision', ''), e.get('geo_method', '')))
    
    # Propose transliteration if name_ar looks like Arabic
    if name_ar and any('\u0600' <= c <= '\u06FF' for c in name_ar):
        # Simple transliteration mapping (very basic)
        print("    >>> PROPOSITION DE TRANSLITTÉRATION (à valider): [À FAIRE MANUELLEMENT]")

# ========== GROUP 3: CLASSIFICATION DE CHAQUE ENTRÉE ==========
print("\n" + "=" * 80)
print("4. CLASSIFICATION DE CHAQUE ENTRÉE")
print("=" * 80)

classifications = []

for m in matched:
    pid = m['place_id']
    geo_id = m.get('geo_id', '')
    name_fr = m.get('name_fr') or m.get('nom_fr') or ''
    name_ar = m.get('name_ar') or ''
    wilaya = m['wilaya']
    commune = m['commune']
    cat = m['cat']
    lat = m['lat']
    lng = m['lng']
    precision = m.get('geo_precision', '')
    method = m.get('geo_method', '')
    
    # Determine status
    status = 'VALIDÉE'
    reasons = []
    
    # Check if in a duplicate coordinate group
    coord_key = (round(lat, 6), round(lng, 6))
    if coord_key in groups_6:
        group_entries = groups_6[coord_key]
        # Check if this entry is the "primary" one (first by some criteria)
        # or if it's a co-located different category
        cats_in_group = set(e['cat'] for e in group_entries)
        if len(cats_in_group) == 1:
            # Same category - probable duplicate
            status = 'DOUBLON PROBABLE'
            reasons.append('Mêmes coordonnées et même catégorie qu\'une autre entrée GeoAlgeria')
        else:
            # Different categories - co-location
            status = 'À VÉRIFIER'
            reasons.append('Co-localisé avec entrée(s) de catégorie(s) différente(s)')
    
    # Check missing French name
    if not name_fr or name_fr.strip() == '':
        if status == 'VALIDÉE':
            status = 'À VÉRIFIER'
        reasons.append('Nom français manquant (nom arabe uniquement: {})'.format(safe(name_ar)[:50]))
    
    # Check precision
    if precision in ('inconnu', ''):
        if status == 'VALIDÉE':
            status = 'À VÉRIFIER'
        reasons.append('Précision GPS inconnue')
    elif precision == 'approximate':
        reasons.append('Précision approximative (centroïde commune)')
    
    # Check method
    if method == 'commune_centroid':
        reasons.append('Géocodage par centroïde de commune')
    
    # Check review status
    review = m.get('review_status', '')
    if review == 'pending':
        reasons.append('Statut révision: en attente')
    elif review == 'rejected':
        reasons.append('Statut révision: rejeté')
    
    classifications.append({
        'place_id': pid,
        'geo_id': geo_id,
        'nom_fr': name_fr,
        'nom_ar': name_ar,
        'wilaya': wilaya,
        'commune': commune,
        'cat': cat,
        'lat': lat,
        'lng': lng,
        'precision': precision,
        'method': method,
        'review_status': review,
        'status': status,
        'reasons': '; '.join(reasons) if reasons else 'Aucun problème détecté'
    })

# Count by status
status_counts = defaultdict(int)
for c in classifications:
    status_counts[c['status']] += 1

print("Répartition par statut:")
for s, cnt in sorted(status_counts.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(s, cnt))

# Detailed list
print("\nDétail par entrée:")
for c in classifications:
    print("\n  place_id={} | geo_id={}".format(c['place_id'], c['geo_id']))
    print("    Statut: {}".format(c['status']))
    print("    FR: {} | AR: {}".format(safe(c['nom_fr']), safe(c['nom_ar'])))
    print("    {} | {} | {} | GPS=({}, {})".format(c['wilaya'], safe(c['commune']), c['cat'], c['lat'], c['lng']))
    print("    Précision: {} | Méthode: {} | Révision: {}".format(
        c['precision'], c['method'], c['review_status']))
    print("    Raisons: {}".format(c['reasons']))

# ========== SUMMARY BY WILAYA/COMMUNE/CATEGORY ==========
print("\n" + "=" * 80)
print("5. RÉPARTITION PAR STATUT ET WILAYA/COMMUNE/CATÉGORIE")
print("=" * 80)

wilaya_status = defaultdict(lambda: defaultdict(int))
cat_status = defaultdict(lambda: defaultdict(int))

for c in classifications:
    wilaya_status[c['wilaya']][c['status']] += 1
    cat_status[c['cat']][c['status']] += 1

print("\nPar wilaya:")
for w in sorted(wilaya_status.keys()):
    counts = wilaya_status[w]
    total = sum(counts.values())
    print("  {}: total={}, VALIDÉE={}, À VÉRIFIER={}, DOUBLON PROBABLE={}".format(
        w, total, counts.get('VALIDÉE', 0), counts.get('À VÉRIFIER', 0), counts.get('DOUBLON PROBABLE', 0)))

print("\nPar catégorie:")
for cat in sorted(cat_status.keys()):
    counts = cat_status[cat]
    total = sum(counts.values())
    print("  {}: total={}, VALIDÉE={}, À VÉRIFIER={}, DOUBLON PROBABLE={}".format(
        cat, total, counts.get('VALIDÉE', 0), counts.get('À VÉRIFIER', 0), counts.get('DOUBLON PROBABLE', 0)))

# ========== RECOMMANDATIONS POUR ENRICHISSEMENT ==========
print("\n" + "=" * 80)
print("6. RECOMMANDATIONS POUR PHASE D'ENRICHISSEMENT CONTACTS")
print("=" * 80)

validated = [c for c in classifications if c['status'] == 'VALIDÉE']
to_verify = [c for c in classifications if c['status'] == 'À VÉRIFIER']
probable_dup = [c for c in classifications if c['status'] == 'DOUBLON PROBABLE']

print("\n>>> VALIDÉES ({}): prêtes pour enrichissement contacts".format(len(validated)))
print(">>> À VÉRIFIER ({}): nécessitent vérification manuelle avant enrichissement".format(len(to_verify)))
print(">>> DOUBLONS PROBABLES ({}): exclure de l'enrichissement, fusion manuelle requise".format(len(probable_dup)))

print("\nDétail VALIDÉES (prêtes enrichissement):")
for c in validated:
    print("  place_id={} | {} | {} | {}".format(c['place_id'], safe(c['nom_fr']), c['wilaya'], c['cat']))

print("\nDétail À VÉRIFIER:")
for c in to_verify:
    print("  place_id={} | {} | {} | {} | GPS=({}, {}) | {}".format(
        c['place_id'], safe(c['nom_fr']), c['wilaya'], c['cat'], c['lat'], c['lng'], c['reasons']))

print("\nDétail DOUBLONS PROBABLES:")
for c in probable_dup:
    print("  place_id={} | {} | {} | {} | GPS=({}, {})".format(
        c['place_id'], safe(c['nom_fr']), c['wilaya'], c['cat'], c['lat'], c['lng']))

conn.close()

# ========== EXPORT CSV REPORT ==========
print("\n" + "=" * 80)
print("7. EXPORT CSV RAPPORT")
print("=" * 80)

output_csv = r'C:\SANTE_DZ_SCRAPER\phase6_5_classification_report.csv'
with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'place_id', 'geo_id', 'nom_fr', 'nom_ar', 'wilaya', 'commune', 'categorie',
        'latitude', 'longitude', 'geo_precision', 'geo_method', 'review_status',
        'statut_classification', 'raisons'
    ])
    writer.writeheader()
    for c in classifications:
        writer.writerow({
            'place_id': c['place_id'],
            'geo_id': c['geo_id'],
            'nom_fr': c['nom_fr'],
            'nom_ar': c['nom_ar'],
            'wilaya': c['wilaya'],
            'commune': c['commune'],
            'categorie': c['cat'],
            'latitude': c['lat'],
            'longitude': c['lng'],
            'geo_precision': c['precision'],
            'geo_method': c['method'],
            'review_status': c['review_status'],
            'statut_classification': c['status'],
            'raisons': c['reasons']
        })

print("Rapport exporté: {}".format(output_csv))
print("Lignes écrites: {}".format(len(classifications)))