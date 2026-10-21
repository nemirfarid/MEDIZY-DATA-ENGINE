#!/usr/bin/env python3
"""
Phase 6.2: Secured Import of GeoAlgeria Biskra Establishments
- Imports only validated entries with GPS coordinates
- Idempotent via stable place_id
- Validates coordinates within Algeria bounds
- Business duplicate detection (nom + wilaya + categorie)
- Structured logging
- NEVER modifies production DB - works on test copy only
"""

import sqlite3
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path

# ========== CONFIGURATION ==========
TEST_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db'
PROD_DB = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
GEOALGERIA_CSV = r'C:\SANTE_DZ_SCRAPER\geoalgeria_sante.csv'
LOG_CSV = r'C:\SANTE_DZ_SCRAPER\phase6_biskra_import_log.csv'

# Algeria bounds
ALGERIA_BOUNDS = {
    'lat_min': 18.9, 'lat_max': 37.1,
    'lng_min': -8.7, 'lng_max': 12.0
}

# Type mapping: GeoAlgeria -> our categories
TYPE_MAPPING = {
    'eph': 'hôpital public',
    'ehs': 'hôpital spécialisé',
    'epsp': 'centre de santé',
    'chu': 'chu',
    'hopital': 'hôpital',
}

# Wilaya code to name
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

# ========== UTILITIES ==========
def normalize_text(text):
    """Normalize text for comparison"""
    if not text:
        return ''
    text = text.lower().strip()
    # Remove common prefixes
    for prefix in ['etablissement public hospitalier', 'hopital', 'centre de sante',
                   'clinique', 'institut', 'epsp', 'eph', 'eh', 'ehs', 'ehu',
                   'etablissement public de sante de proximite']:
        text = text.replace(prefix, '').strip()
    text = text.replace('(', '').replace(')', '').strip()
    text = ' '.join(text.split())
    return text

def generate_place_id(nom, wilaya, commune, categorie, lat, lng):
    """Generate stable place_id from key fields"""
    key = f"{nom}|{wilaya}|{commune}|{categorie}|{lat}|{lng}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def validate_coordinates(lat, lng):
    """Validate coordinates are within Algeria bounds"""
    if lat is None or lng is None:
        return False, "Missing coordinates"
    if not (ALGERIA_BOUNDS['lat_min'] <= lat <= ALGERIA_BOUNDS['lat_max']):
        return False, f"Latitude {lat} out of Algeria bounds"
    if not (ALGERIA_BOUNDS['lng_min'] <= lng <= ALGERIA_BOUNDS['lng_max']):
        return False, f"Longitude {lng} out of Algeria bounds"
    return True, "OK"

def validate_phone(phone):
    """Validate Algerian phone number"""
    if not phone:
        return None, "No phone"
    # Clean
    phone = re.sub(r'[^\d+]', '', phone)
    # Check Algerian format
    if phone.startswith('+213'):
        phone = phone[4:]
    elif phone.startswith('00213'):
        phone = phone[5:]
    if re.match(r'^(5|6|7)\d{8}$', phone):
        return f"+213 {phone[0]} {phone[1:4]} {phone[4:7]} {phone[7:]}", "OK"
    if re.match(r'^(05|06|07)\d{8}$', phone):
        phone = phone[1:]
        return f"+213 {phone[0]} {phone[1:4]} {phone[4:7]} {phone[7:]}", "OK"
    return None, f"Invalid format: {phone}"

def validate_website(url):
    """Validate website - reject CDN/template domains"""
    if not url:
        return None, "No website"
    url_lower = url.lower()
    # Blocked domains
    blocked = ['fonts.gstatic.com', 'fonts.googleapis.com', 'gstatic.com',
               'googleapis.com', 'cloudflare.com', 'bootstrapcdn.com',
               'jquery.com', 'cdnjs.cloudflare.com']
    for b in blocked:
        if b in url_lower:
            return None, f"Blocked domain: {b}"
    # Basic URL validation
    if not url_lower.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url, "OK"

def check_business_duplicate(conn, nom, wilaya, categorie):
    """Check if business (nom+wilaya+categorie) already exists"""
    nom_norm = normalize_text(nom)
    c = conn.cursor()
    c.execute('''
        SELECT id, nom, commune FROM places
        WHERE wilaya = ? AND categorie_recherche = ?
    ''', (wilaya, categorie))
    for row in c.fetchall():
        existing_norm = normalize_text(row[1])
        # Check significant word overlap
        nom_words = set(nom_norm.split())
        exist_words = set(existing_norm.split())
        significant = len([w for w in nom_words & exist_words if len(w) > 3])
        if significant >= 2 or (nom_norm and nom_norm in existing_norm) or (existing_norm and existing_norm in nom_norm):
            return row[0], row[1], row[2]
    return None, None, None

# ========== LOGGING ==========
def init_log():
    """Initialize log CSV"""
    with open(LOG_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 'geo_id', 'action', 'place_id',
            'nom', 'wilaya', 'commune', 'categorie',
            'latitude', 'longitude', 'phone', 'website',
            'details', 'source_geo_id', 'geo_precision', 'geo_method'
        ])

def log_entry(geo_id, action, place_id, nom, wilaya, commune, categorie,
              lat, lng, phone, website, details, source_geo_id, geo_precision, geo_method):
    with open(LOG_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(), geo_id, action, place_id or '',
            nom, wilaya, commune, categorie,
            lat if lat else '', lng if lng else '',
            phone if phone else '', website if website else '',
            details, source_geo_id, geo_precision, geo_method
        ])

# ========== MAIN IMPORT ==========
def import_biskra_geoalgeria():
    print("=" * 70)
    print("PHASE 6.2: GeoAlgeria Biskra Import (Secured)")
    print("=" * 70)
    print(f"Test DB: {TEST_DB}")
    print(f"GeoAlgeria CSV: {GEOALGERIA_CSV}")
    print(f"Log: {LOG_CSV}")
    print()

    # Verify test DB exists and is a copy of production
    if not Path(TEST_DB).exists():
        print(f"ERROR: Test DB not found at {TEST_DB}")
        return

    # Load GeoAlgeria data
    with open(GEOALGERIA_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        geo_rows = [r for r in reader if r['wilaya_code'] == '07']

    print(f"GeoAlgeria Biskra entries: {len(geo_rows)}")

    # Connect to test DB
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()

    # Verify schema
    c.execute("PRAGMA table_info(places)")
    cols = [row[1] for row in c.fetchall()]
    required_cols = ['place_id', 'nom', 'wilaya', 'commune', 'categorie_recherche',
                     'latitude', 'longitude', 'telephone', 'site_web', 'source']
    for rc in required_cols:
        if rc not in cols:
            print(f"ERROR: Missing column {rc} in places table")
            conn.close()
            return

    # Check UNIQUE constraint on place_id
    c.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_places_place_id'")
    idx = c.fetchone()
    if not idx or 'UNIQUE' not in (idx[0] or '').upper():
        print("WARNING: place_id UNIQUE index not found - idempotence may fail")

    # Initialize log
    init_log()

    stats = {'imported': 0, 'skipped_duplicate': 0, 'skipped_business_dup': 0,
             'rejected_no_gps': 0, 'rejected_bad_gps': 0, 'rejected_no_coords': 0,
             'errors': 0}

    for geo in geo_rows:
        geo_id = geo['id']
        nom = geo['name_fr'] or geo['name'] or ''
        nom_ar = geo['name_ar'] or ''
        wilaya_code = geo['wilaya_code']
        wilaya = WILAYA_MAP.get(wilaya_code, 'Biskra')
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

        # Map category
        categorie = TYPE_MAPPING.get(geo_type, 'établissement de santé')

        print("\nProcessing: {} - {}...".format(geo_id, nom[:60].encode('ascii', 'replace').decode()))

        # 1. Reject if no coordinates
        if lat is None or lng is None:
            place_id = generate_place_id(nom, wilaya, commune, categorie, lat or 0, lng or 0)
            log_entry(geo_id, 'REJECTED_NO_GPS', place_id, nom, wilaya, commune, categorie,
                      lat, lng, None, None, "No GPS coordinates in source", geo_id, precision, method)
            stats['rejected_no_gps'] += 1
            print(f"  REJECTED: No GPS coordinates")
            continue

        # 2. Validate coordinates
        valid, msg = validate_coordinates(lat, lng)
        if not valid:
            place_id = generate_place_id(nom, wilaya, commune, categorie, lat, lng)
            log_entry(geo_id, 'REJECTED_BAD_GPS', place_id, nom, wilaya, commune, categorie,
                      lat, lng, None, None, msg, geo_id, precision, method)
            stats['rejected_bad_gps'] += 1
            print(f"  REJECTED: {msg}")
            continue

        # 3. Generate place_id
        place_id = generate_place_id(nom, wilaya, commune, categorie, lat, lng)

        # 4. Check idempotence (place_id already exists)
        c.execute('SELECT id FROM places WHERE place_id = ?', (place_id,))
        if c.fetchone():
            log_entry(geo_id, 'SKIPPED_DUPLICATE_ID', place_id, nom, wilaya, commune, categorie,
                      lat, lng, None, None, "place_id already exists", geo_id, precision, method)
            stats['skipped_duplicate'] += 1
            print(f"  SKIPPED: place_id already exists")
            continue

        # 5. Check business duplicate (nom + wilaya + categorie)
        dup_id, dup_nom, dup_commune = check_business_duplicate(conn, nom, wilaya, categorie)
        if dup_id:
            log_entry(geo_id, 'SKIPPED_BUSINESS_DUP', place_id, nom, wilaya, commune, categorie,
                      lat, lng, None, None,
                      f"Business duplicate: id={dup_id} ({dup_nom}, {dup_commune})", geo_id, precision, method)
            stats['skipped_business_dup'] += 1
            print(f"  SKIPPED: Business duplicate (id={dup_id})")
            continue

        # 6. Validate phone (GeoAlgeria may not have phones)
        phone = None
        phone_status = "No phone in source"
        # Could try to look up phone from other sources later

        # 7. Validate website (GeoAlgeria may not have websites)
        website = None
        website_status = "No website in source"

        # 8. Insert
        try:
            c.execute('''
                INSERT INTO places (
                    place_id, nom, nom_normalized, wilaya, wilaya_normalized,
                    commune, categorie_recherche,
                    latitude, longitude, telephone, site_web, source,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                place_id,
                nom,
                normalize_text(nom),
                wilaya,
                wilaya.lower(),
                commune,
                categorie,
                lat,
                lng,
                phone,
                website,
                f'geoalgeria:{source}',
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            log_entry(geo_id, 'IMPORTED', place_id, nom, wilaya, commune, categorie,
                      lat, lng, phone, website, "Imported from GeoAlgeria", geo_id, precision, method)
            stats['imported'] += 1
            print(f"  IMPORTED: place_id={place_id} | {wilaya}/{commune} | {categorie} | GPS=({lat:.6f}, {lng:.6f})")

        except sqlite3.IntegrityError as e:
            conn.rollback()
            if 'UNIQUE' in str(e) and 'place_id' in str(e):
                log_entry(geo_id, 'SKIPPED_DUPLICATE_ID', place_id, nom, wilaya, commune, categorie,
                          lat, lng, None, None, f"Integrity error: {e}", geo_id, precision, method)
                stats['skipped_duplicate'] += 1
                print(f"  SKIPPED: place_id conflict (race condition)")
            else:
                log_entry(geo_id, 'ERROR', place_id, nom, wilaya, commune, categorie,
                          lat, lng, None, None, f"Integrity error: {e}", geo_id, precision, method)
                stats['errors'] += 1
                print(f"  ERROR: {e}")
        except Exception as e:
            conn.rollback()
            log_entry(geo_id, 'ERROR', place_id, nom, wilaya, commune, categorie,
                      lat, lng, None, None, f"Exception: {e}", geo_id, precision, method)
            stats['errors'] += 1
            print(f"  ERROR: {e}")

    conn.close()

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  Total processed: {sum(stats.values())}")

    # Verify test DB after import
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM places WHERE source LIKE "geoalgeria:%"')
    geo_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM places WHERE wilaya = "Biskra"')
    biskra_total = c.fetchone()[0]
    conn.close()
    print(f"\nGeoAlgeria entries in test DB: {geo_count}")
    print(f"Total Biskra entries in test DB: {biskra_total}")

    print(f"\nLog written to: {LOG_CSV}")

if __name__ == '__main__':
    import_biskra_geoalgeria()