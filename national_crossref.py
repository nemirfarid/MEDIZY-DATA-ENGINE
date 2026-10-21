import sqlite3
import csv
import hashlib
from datetime import datetime

# Wilaya code to name mapping
WILAYA_MAP = {
    '01': 'Adrar', '02': 'Chlef', '03': 'Laghouat', '04': 'Oum El Bouaghi',
    '05': 'Batna', '06': 'Béjaïa', '07': 'Biskra', '08': 'Béchar',
    '09': 'Blida', '10': 'Bouira', '11': 'Tamanrasset', '12': 'Tébessa',
    '13': 'Tlemcen', '14': 'Tiaret', '15': 'Tizi Ouzou', '16': 'Alger',
    '17': 'Djelfa', '18': 'Jijel', '19': 'Sétif', '20': 'Saïda',
    '21': 'Skikda', '22': 'Sidi Bel Abbès', '23': 'Annaba', '24': 'Guelma',
    '25': 'Constantine', '26': 'Médéa', '27': 'Mostaganem', '28': 'M\'Sila',
    '29': 'Mascara', '30': 'Ouargla', '31': 'Oran', '32': 'El Bayadh',
    '33': 'Illizi', '34': 'Bordj Bou Arréridj', '35': 'Boumerdès',
    '36': 'El Tarf', '37': 'Tindouf', '38': 'Tissemsilt', '39': 'El Oued',
    '40': 'Khenchela', '41': 'Souk Ahras', '42': 'Tipaza', '43': 'Mila',
    '44': 'Aïn Defla', '45': 'Naâma', '46': 'Aïn Témouchent', '47': 'Ghardaïa',
    '48': 'Relizane', '49': 'Timimoun', '50': 'Bordj Badji Mokhtar',
    '51': 'Ouled Djellal', '52': 'Béni Abbès', '53': 'In Salah',
    '54': 'In Guezzam', '55': 'Touggourt', '56': 'Djanet', '57': 'El M\'Ghair',
    '58': 'El Meniaa'
}

TYPE_MAPPING = {
    'eph': 'hôpital public',
    'ehs': 'hôpital spécialisé',
    'epsp': 'centre de santé',
    'chu': 'chu',
    'hopital': 'hôpital',
}

def normalize_text(text):
    if not text:
        return ''
    text = text.lower().strip()
    for prefix in ['etablissement public hospitalier', 'hopital', 'centre de sante',
                   'clinique', 'institut', 'epsp', 'eph', 'eh', 'ehs', 'ehu',
                   'etablissement public de sante de proximite']:
        text = text.replace(prefix, '').strip()
    text = text.replace('(', '').replace(')', '').strip()
    text = ' '.join(text.split())
    return text

def generate_place_id(nom, wilaya, commune, categorie, lat, lng):
    key = "{}|{}|{}|{}|{}|{}".format(nom, wilaya, commune, categorie, lat, lng)
    return hashlib.sha256(key.encode()).hexdigest()[:16]

# Load GeoAlgeria data
with open(r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    geo_rows = list(reader)

# Connect to production DB
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Build DB lookup by wilaya
db_by_wilaya = {}
c.execute('SELECT id, nom, nom_normalized, wilaya, commune, categorie_recherche, latitude, longitude, source FROM places')
for row in c.fetchall():
    db_id, nom, nom_norm, wilaya, commune, cat, lat, lng, source = row
    if wilaya not in db_by_wilaya:
        db_by_wilaya[wilaya] = []
    db_by_wilaya[wilaya].append({
        'id': db_id, 'nom': nom, 'nom_norm': nom_norm, 'wilaya': wilaya,
        'commune': commune, 'cat': cat, 'lat': lat, 'lng': lng, 'source': source
    })

print("DB loaded: {} wilayas covered".format(len(db_by_wilaya)))

# Classify each GeoAlgeria entry
results = []

for geo in geo_rows:
    geo_id = geo['id']
    nom = geo['name_fr'] or geo['name'] or ''
    nom_ar = geo['name_ar'] or ''
    wilaya_code = geo['wilaya_code']
    wilaya = WILAYA_MAP.get(wilaya_code, 'Inconnu')
    commune = geo['commune'] or ''
    commune_code = geo['commune_code'] or ''
    geo_type = geo['type']
    type_label = geo['type_label_fr'] or geo_type
    lat = float(geo['lat']) if geo['lat'] else None
    lng = float(geo['lng']) if geo['lng'] else None
    precision = geo['geo_precision'] or ''
    method = geo['geo_method'] or ''
    source = geo['source'] or 'geoalgeria'
    refs = geo['refs'] or ''
    
    categorie = TYPE_MAPPING.get(geo_type, 'établissement de santé')
    
    # Check for existing match in DB
    status = 'nouveau_probable'
    matched_db_id = None
    matched_db_nom = None
    match_reason = ''
    match_confidence = 'low'
    
    if wilaya in db_by_wilaya:
        geo_norm = normalize_text(nom)
        geo_words = set(geo_norm.split())
        
        best_match = None
        best_score = 0
        
        for db_entry in db_by_wilaya[wilaya]:
            db_norm = normalize_text(db_entry['nom'] or '')
            db_words = set(db_norm.split())
            
            # Significant word overlap (words > 3 chars)
            significant_overlap = len([w for w in geo_words & db_words if len(w) > 3])
            
            # Check substring
            substring_match = (geo_norm and geo_norm in db_norm) or (db_norm and db_norm in geo_norm)
            
            # GPS proximity if both have coordinates
            gps_match = False
            if lat and lng and db_entry['lat'] and db_entry['lng']:
                dist = ((lat - db_entry['lat'])**2 + (lng - db_entry['lng'])**2)**0.5
                if dist < 0.001:  # ~100m
                    gps_match = True
            
            score = significant_overlap
            if substring_match:
                score += 2
            if gps_match:
                score += 3
            
            if score > best_score:
                best_score = score
                best_match = db_entry
        
        if best_match and best_score >= 3:
            status = 'doublon_certain'
            matched_db_id = best_match['id']
            matched_db_nom = best_match['nom']
            match_reason = 'score={}, overlap_significatif, gps_proche={}'.format(
                best_score, best_match['lat'] and best_match['lng'] and lat and lng)
            match_confidence = 'high'
        elif best_match and best_score >= 2:
            status = 'doublon_possible'
            matched_db_id = best_match['id']
            matched_db_nom = best_match['nom']
            match_reason = 'score={}, overlap_significatif'.format(best_score)
            match_confidence = 'medium'
        elif best_match and best_score >= 1:
            status = 'doublon_possible'
            matched_db_id = best_match['id']
            matched_db_nom = best_match['nom']
            match_reason = 'score={}, overlap_faible'.format(best_score)
            match_confidence = 'low'
    
    # Reject if no GPS
    if lat is None or lng is None:
        status = 'rejete_pas_gps'
        match_reason = 'Pas de coordonnées GPS dans la source'
    
    results.append({
        'geo_id': geo_id,
        'nom': nom,
        'nom_ar': nom_ar,
        'wilaya_code': wilaya_code,
        'wilaya': wilaya,
        'commune': commune,
        'commune_code': commune_code,
        'type': geo_type,
        'type_label': type_label,
        'categorie': categorie,
        'lat': lat,
        'lng': lng,
        'precision': precision,
        'method': method,
        'source': source,
        'refs': refs,
        'status': status,
        'matched_db_id': matched_db_id,
        'matched_db_nom': matched_db_nom,
        'match_reason': match_reason,
        'match_confidence': match_confidence,
        'place_id': generate_place_id(nom, wilaya, commune, categorie, lat or 0, lng or 0)
    })

# Write national candidates CSV
output_csv = r'C:\SANTE_DZ_SCRAPER\phase6_national_candidates.csv'
with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'geo_id', 'nom', 'nom_ar', 'wilaya_code', 'wilaya', 'commune', 'commune_code',
        'type', 'type_label', 'categorie', 'lat', 'lng', 'precision', 'method', 'source',
        'refs', 'status', 'matched_db_id', 'matched_db_nom', 'match_reason',
        'match_confidence', 'place_id'
    ])
    writer.writeheader()
    for r in results:
        writer.writerow(r)

print("CSV national ecrit: {}".format(output_csv))
print("Total: {}".format(len(results)))

# Status counts
status_counts = {}
for r in results:
    status_counts[r['status']] = status_counts.get(r['status'], 0) + 1

print("\nStatuts:")
for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
    print("  {}: {}".format(s, c))

# By wilaya
wilaya_stats = {}
for r in results:
    w = r['wilaya']
    if w not in wilaya_stats:
        wilaya_stats[w] = {'total': 0, 'nouveau': 0, 'doublon_certain': 0, 'doublon_possible': 0, 'rejete': 0}
    wilaya_stats[w]['total'] += 1
    if r['status'] == 'nouveau_probable':
        wilaya_stats[w]['nouveau'] += 1
    elif r['status'] == 'doublon_certain':
        wilaya_stats[w]['doublon_certain'] += 1
    elif r['status'] == 'doublon_possible':
        wilaya_stats[w]['doublon_possible'] += 1
    elif r['status'] == 'rejete_pas_gps':
        wilaya_stats[w]['rejete'] += 1

print("\nPar wilaya (top 10 nouveaux):")
sorted_wilayas = sorted(wilaya_stats.items(), key=lambda x: -x[1]['nouveau'])
for w, stats in sorted_wilayas[:15]:
    print("  {}: total={}, nouveaux={}, doublons_certains={}, doublons_possibles={}, rejetes={}".format(
        w, stats['total'], stats['nouveau'], stats['doublon_certain'], stats['doublon_possible'], stats['rejete']))

conn.close()