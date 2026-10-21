import sqlite3
import csv
import hashlib
from datetime import datetime

# Configuration
TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_national_test.db'
CANDIDATES_CSV = r'C:\SANTE_DZ_SCRAPER\phase6_national_candidates.csv'
LOG_CSV = r'C:\SANTE_DZ_SCRAPER\phase6_national_import_log.csv'

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

ALGERIA_BOUNDS = {'lat_min': 18.9, 'lat_max': 37.1, 'lng_min': -8.7, 'lng_max': 12.0}

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

def validate_coordinates(lat, lng):
    if lat is None or lng is None:
        return False, "Missing coordinates"
    if not (ALGERIA_BOUNDS['lat_min'] <= lat <= ALGERIA_BOUNDS['lat_max']):
        return False, "Latitude {} out of bounds".format(lat)
    if not (ALGERIA_BOUNDS['lng_min'] <= lng <= ALGERIA_BOUNDS['lng_max']):
        return False, "Longitude {} out of bounds".format(lng)
    return True, "OK"

def check_business_duplicate(conn, nom, wilaya, categorie):
    nom_norm = normalize_text(nom)
    c = conn.cursor()
    c.execute('''
        SELECT id, nom, commune FROM places
        WHERE wilaya = ? AND categorie_recherche = ?
    ''', (wilaya, categorie))
    for row in c.fetchall():
        existing_norm = normalize_text(row[1])
        nom_words = set(nom_norm.split())
        exist_words = set(existing_norm.split())
        significant = len([w for w in nom_words & exist_words if len(w) > 3])
        if significant >= 2 or (nom_norm and nom_norm in existing_norm) or (existing_norm and existing_norm in nom_norm):
            return row[0], row[1], row[2]
    return None, None, None

def init_log():
    with open(LOG_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 'geo_id', 'action', 'place_id',
            'nom', 'wilaya', 'commune', 'categorie',
            'latitude', 'longitude', 'phone', 'website',
            'details', 'matched_db_id', 'matched_db_nom', 'match_reason'
        ])

def log_entry(geo_id, action, place_id, nom, wilaya, commune, categorie,
              lat, lng, phone, website, details, matched_db_id, matched_db_nom, match_reason):
    with open(LOG_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(), geo_id, action, place_id or '',
            nom, wilaya, commune, categorie,
            lat if lat else '', lng if lng else '',
            phone if phone else '', website if website else '',
            details, matched_db_id if matched_db_id else '', 
            matched_db_nom if matched_db_nom else '', match_reason
        ])

def import_national():
    print("=" * 70)
    print("PHASE 6.3: Import National Simule (Test DB)")
    print("=" * 70)

    # Load candidates
    with open(CANDIDATES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    print("Candidats a traiter: {}".format(len(candidates)))

    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()

    init_log()

    stats = {'imported': 0, 'skipped_duplicate': 0, 'skipped_business_dup': 0,
             'rejected_no_gps': 0, 'rejected_bad_gps': 0, 'skipped_certain_dup': 0,
             'skipped_possible_dup': 0, 'errors': 0}

    for cand in candidates:
        geo_id = cand['geo_id']
        nom = cand['nom']
        wilaya = cand['wilaya']
        commune = cand['commune']
        cat = cand['categorie']
        lat = float(cand['lat']) if cand['lat'] else None
        lng = float(cand['lng']) if cand['lng'] else None
        status = cand['status']
        matched_db_id = cand['matched_db_id'] or None
        matched_db_nom = cand['matched_db_nom'] or None
        match_reason = cand['match_reason'] or ''

        # Only import 'nouveau_probable' with GPS
        if status != 'nouveau_probable':
            if status == 'rejete_pas_gps':
                stats['rejected_no_gps'] += 1
                log_entry(geo_id, 'REJECTED_NO_GPS', '', nom, wilaya, commune, cat,
                          lat, lng, '', '', 'Pas de GPS', matched_db_id, matched_db_nom, match_reason)
            elif status == 'doublon_certain':
                stats['skipped_certain_dup'] += 1
                log_entry(geo_id, 'SKIPPED_CERTAIN_DUP', '', nom, wilaya, commune, cat,
                          lat, lng, '', '', 'Doublon certain: {}'.format(match_reason), matched_db_id, matched_db_nom, match_reason)
            elif status == 'doublon_possible':
                stats['skipped_possible_dup'] += 1
                log_entry(geo_id, 'SKIPPED_POSSIBLE_DUP', '', nom, wilaya, commune, cat,
                          lat, lng, '', '', 'Doublon possible: {}'.format(match_reason), matched_db_id, matched_db_nom, match_reason)
            continue

        # Validate coordinates
        valid, msg = validate_coordinates(lat, lng)
        if not valid:
            stats['rejected_bad_gps'] += 1
            place_id = generate_place_id(nom, wilaya, commune, cat, lat, lng)
            log_entry(geo_id, 'REJECTED_BAD_GPS', place_id, nom, wilaya, commune, cat,
                      lat, lng, '', '', msg, matched_db_id, matched_db_nom, match_reason)
            continue

        place_id = generate_place_id(nom, wilaya, commune, cat, lat, lng)

        # Check idempotence
        c.execute('SELECT id FROM places WHERE place_id = ?', (place_id,))
        if c.fetchone():
            stats['skipped_duplicate'] += 1
            log_entry(geo_id, 'SKIPPED_DUPLICATE_ID', place_id, nom, wilaya, commune, cat,
                      lat, lng, '', '', 'place_id already exists', matched_db_id, matched_db_nom, match_reason)
            continue

        # Check business duplicate
        dup_id, dup_nom, dup_commune = check_business_duplicate(conn, nom, wilaya, cat)
        if dup_id:
            stats['skipped_business_dup'] += 1
            log_entry(geo_id, 'SKIPPED_BUSINESS_DUP', place_id, nom, wilaya, commune, cat,
                      lat, lng, '', '', 'Business duplicate: id={} ({}, {})'.format(dup_id, dup_nom, dup_commune), matched_db_id, matched_db_nom, match_reason)
            continue

        # Insert
        try:
            c.execute('''
                INSERT INTO places (
                    place_id, nom, nom_normalized, wilaya, wilaya_normalized,
                    commune, categorie_recherche,
                    latitude, longitude, telephone, site_web, source,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                place_id, nom, normalize_text(nom), wilaya, wilaya.lower(),
                commune, cat, lat, lng, None, None,
                'geoalgeria:msp', datetime.now().isoformat(), datetime.now().isoformat()
            ))
            conn.commit()
            stats['imported'] += 1
            log_entry(geo_id, 'IMPORTED', place_id, nom, wilaya, commune, cat,
                      lat, lng, '', '', 'Imported from GeoAlgeria', matched_db_id, matched_db_nom, match_reason)
        except sqlite3.IntegrityError as e:
            conn.rollback()
            if 'UNIQUE' in str(e) and 'place_id' in str(e):
                stats['skipped_duplicate'] += 1
                log_entry(geo_id, 'SKIPPED_DUPLICATE_ID', place_id, nom, wilaya, commune, cat,
                          lat, lng, '', '', 'Integrity error: {}'.format(e), matched_db_id, matched_db_nom, match_reason)
            else:
                stats['errors'] += 1
                log_entry(geo_id, 'ERROR', place_id, nom, wilaya, commune, cat,
                          lat, lng, '', '', 'Integrity error: {}'.format(e), matched_db_id, matched_db_nom, match_reason)
        except Exception as e:
            conn.rollback()
            stats['errors'] += 1
            log_entry(geo_id, 'ERROR', place_id, nom, wilaya, commune, cat,
                      lat, lng, '', '', 'Exception: {}'.format(e), matched_db_id, matched_db_nom, match_reason)

    conn.close()

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    for k, v in stats.items():
        print("  {}: {}".format(k, v))
    print("  Total: {}".format(sum(stats.values())))

    # Verify
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM places WHERE source LIKE "geoalgeria:%"')
    geo_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places')
    total = c.fetchone()[0]
    conn.close()
    print("\nGeoAlgeria entries in test DB: {}".format(geo_count))
    print("Total entries in test DB: {}".format(total))
    print("Log: {}".format(LOG_CSV))

if __name__ == '__main__':
    import_national()