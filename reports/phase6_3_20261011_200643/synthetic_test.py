"""
Test synthétique pour phase6_import_new_secured.py
Teste les cas limites sur une base isolée.
"""

import sqlite3
import csv
import time
import urllib.request
import urllib.parse
import json
import os
import re
from datetime import datetime
from typing import Optional, Tuple, Dict, List, Any

# ============================================================================
# CONFIGURATION — BASE SYNTHÉTIQUE ISOLÉE
# ============================================================================
SYNTH_DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_synthetic.db'
SYNTH_CSV = r'D:\SANTE_DZ_EXPORTS\miph_synthetic_test.csv'
SYNTH_LOG = r'C:\SANTE_DZ_SCRAPER\phase6_synthetic_test_log.csv'

ALGERIA_BOUNDS = {
    'lat_min': 18.5, 'lat_max': 37.5,
    'lon_min': -9.0, 'lon_max': 12.5
}

MIPH_TYPE_TO_CATEGORIE = {
    'CHU': 'hôpital', 'EPH': 'hôpital', 'EH': 'hôpital', 'EHS': 'clinique',
    'EHU': 'hôpital', 'EPSP': 'centre de santé', 'DSP': 'Structure',
    'INSTITUT/FORMATION': 'Institut de formation', 'EST': 'Institut de formation',
    'INFSPM': 'Institut de formation', 'INFPM': 'Institut de formation',
    'IFPM': 'Institut de formation', 'IFSM': 'Institut de formation',
    'DRH': 'Direction', 'Structure': 'Structure',
}


# ============================================================================
# UTILITAIRES (copie de phase6_import_new_secured.py)
# ============================================================================
def validate_coordinates(lat: Optional[float], lon: Optional[float]) -> Tuple[bool, str]:
    if lat is None or lon is None:
        return False, 'COORD_NULL'
    if not (ALGERIA_BOUNDS['lat_min'] <= lat <= ALGERIA_BOUNDS['lat_max']):
        return False, f'LAT_OUT_OF_BOUNDS ({lat})'
    if not (ALGERIA_BOUNDS['lon_min'] <= lon <= ALGERIA_BOUNDS['lon_max']):
        return False, f'LON_OUT_OF_BOUNDS ({lon})'
    return True, 'OK'


def validate_phone(phone: Optional[str]) -> Tuple[bool, str]:
    if not phone:
        return False, 'PHONE_EMPTY'
    clean = re.sub(r'[^\d]', '', phone)
    if clean.startswith('01'):
        return False, 'PHONE_INVALID_PREFIX_01'
    if re.match(r'^0[5679]\d{8}$', clean):
        return True, 'OK'
    if re.match(r'^0[234]\d{7,8}$', clean):
        return True, 'OK_LANDLINE'
    return False, f'PHONE_INVALID_FORMAT ({phone})'


def validate_website(url: Optional[str]) -> Tuple[bool, str]:
    if not url:
        return False, 'URL_EMPTY'
    suspicious_domains = [
        'fonts.gstatic.com', 'googleapis.com', 'gstatic.com',
        'cloudflare.com', 'bootstrapcdn.com', 'jquery.com',
        'cdnjs.cloudflare.com', 'unpkg.com', 'jsdelivr.net'
    ]
    url_lower = url.lower()
    for dom in suspicious_domains:
        if dom in url_lower:
            return False, f'URL_SUSPICIOUS_CDN ({dom})'
    if not re.match(r'^https?://', url_lower):
        return False, 'URL_NO_SCHEME'
    return True, 'OK'


def normalize_arabic(text: str) -> str:
    if not text:
        return ''
    text = text.replace('D?centralis', '').replace('&eacute;', 'é').replace('&Eacute;', 'É')
    text = text.replace('&egrave;', 'è').replace('&Egrave;', 'È')
    return text.strip()


def build_nom_normalized(name_fr: str) -> str:
    n = name_fr.lower().strip()
    for prefix in ['établissement public hospitalier', 'etablissement public hospitalier',
                   'hôpital', 'hopital', 'centre de santé', 'centre de sante',
                   'clinique', 'institut', 'epsp', 'eph', 'eh', 'ehs', 'ehu']:
        n = n.replace(prefix, '').strip()
    n = n.replace('(', '').replace(')', '').strip()
    n = re.sub(r'\s+', ' ', n)
    return n


def geocode_postal(wilaya_code: int, postal_code: str) -> Tuple[Optional[float], Optional[float], Optional[str], str]:
    if not postal_code or str(postal_code).strip() in ('0', '00000', ''):
        return None, None, None, 'REJECTED_POSTAL_ZERO'

    query = f"{postal_code}, Algerie"
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': query, 'format': 'json', 'limit': '5', 'addressdetails': '1',
    })

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        time.sleep(1.1)

        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            valid, reason = validate_coordinates(lat, lon)
            if not valid:
                return None, None, None, f'REJECTED_GEO_BOUNDS_{reason}'
            addr = data[0].get('address', {})
            commune = addr.get('town') or addr.get('village') or addr.get('city') or None
            return lat, lon, commune, 'NOMINATIM_POSTAL'
    except Exception as e:
        return None, None, None, f'NOMINATIM_ERROR_{type(e).__name__}'

    return None, None, None, 'NOMINATIM_NO_RESULT'


def check_business_duplicate(cursor: sqlite3.Cursor, nom_normalized: str, wilaya: str, categorie: str) -> Optional[int]:
    cursor.execute('''
        SELECT id FROM places
        WHERE nom_normalized = ? AND wilaya_normalized = ? AND categorie_recherche = ?
    ''', (nom_normalized, wilaya.lower(), categorie))
    row = cursor.fetchone()
    return row[0] if row else None


def init_log_file():
    if not os.path.exists(SYNTH_LOG):
        with open(SYNTH_LOG, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'action', 'pdf_id', 'place_id', 'nom', 'wilaya',
                'postal_code', 'latitude', 'longitude', 'commune',
                'geocode_source', 'validation_status', 'duplicate_check',
                'phone_validation', 'website_validation', 'error_detail'
            ])


def log_entry(data: Dict[str, Any]):
    row = [
        datetime.now().isoformat(),
        data.get('action', ''), data.get('pdf_id', ''), data.get('place_id', ''),
        data.get('nom', ''), data.get('wilaya', ''), data.get('postal_code', ''),
        data.get('latitude', ''), data.get('longitude', ''), data.get('commune', ''),
        data.get('geocode_source', ''), data.get('validation_status', ''),
        data.get('duplicate_check', ''), data.get('phone_validation', ''),
        data.get('website_validation', ''), data.get('error_detail', ''),
    ]
    with open(SYNTH_LOG, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(row)


def import_synthetic_entities(db_path: str = SYNTH_DB_PATH) -> Dict[str, int]:
    init_log_file()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    stats = {
        'total_csv': 0, 'imported': 0, 'skipped_duplicate_id': 0,
        'skipped_business_duplicate': 0, 'geocoded': 0, 'not_geocoded': 0,
        'rejected_postal_zero': 0, 'rejected_geo_bounds': 0,
        'rejected_nominatim': 0, 'errors': 0
    }

    with open(SYNTH_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats['total_csv'] += 1

            pdf_id = row['pdf_id'].strip()
            name_fr = row['etab_fr'].strip()
            name_ar = normalize_arabic(row.get('etab_ar', ''))
            wilaya = row['wilaya'].strip()
            wilaya_code = int(row['wilaya_code'])
            postal_code = row['code_postal'].strip()
            type_etab = row['type_etab'].strip()
            categorie = MIPH_TYPE_TO_CATEGORIE.get(type_etab, 'Structure')

            place_id = f"miph_{pdf_id}"
            nom_normalized = build_nom_normalized(name_fr)

            print(f"\n--- Test {pdf_id}: {name_fr} ---")
            print(f"  place_id: {place_id}".encode('ascii', 'replace').decode())
            print(f"  nom_normalized: {nom_normalized}".encode('ascii', 'replace').decode())
            print(f"  wilaya: {wilaya}, categorie: {categorie}".encode('ascii', 'replace').decode())
            print(f"  postal_code: {postal_code}".encode('ascii', 'replace').decode())

            # 1. Vérifier place_id
            c.execute('SELECT id FROM places WHERE place_id = ?', (place_id,))
            if c.fetchone():
                stats['skipped_duplicate_id'] += 1
                log_entry({'action': 'SKIP_DUPLICATE_ID', 'pdf_id': pdf_id, 'place_id': place_id,
                          'nom': name_fr, 'wilaya': wilaya, 'postal_code': postal_code,
                          'validation_status': 'DUPLICATE_ID', 'duplicate_check': 'EXISTS_BY_PLACE_ID',
                          'error_detail': 'place_id already exists in DB'})
                print(f"  RESULT: SKIP_DUPLICATE_ID")
                continue

            # 2. Vérifier doublon métier
            existing_id = check_business_duplicate(c, nom_normalized, wilaya, categorie)
            if existing_id:
                stats['skipped_business_duplicate'] += 1
                log_entry({'action': 'SKIP_BUSINESS_DUPLICATE', 'pdf_id': pdf_id, 'place_id': place_id,
                          'nom': name_fr, 'wilaya': wilaya, 'postal_code': postal_code,
                          'validation_status': 'DUPLICATE_BUSINESS', 'duplicate_check': f'EXISTS_ID_{existing_id}',
                          'error_detail': f'Business duplicate: same name+wilaya+cat (id={existing_id})'})
                print(f"  RESULT: SKIP_BUSINESS_DUPLICATE (existing id={existing_id})")
                continue

            # 3. Géocodage
            lat, lon, commune, geo_source = geocode_postal(wilaya_code, postal_code)

            if geo_source == 'REJECTED_POSTAL_ZERO':
                stats['rejected_postal_zero'] += 1
                validation_status = 'POSTAL_ZERO_NO_GEOCODE'
            elif geo_source.startswith('REJECTED_GEO_BOUNDS'):
                stats['rejected_geo_bounds'] += 1
                validation_status = 'GEO_OUT_OF_BOUNDS'
            elif geo_source.startswith('NOMINATIM_ERROR') or geo_source == 'NOMINATIM_NO_RESULT':
                stats['rejected_nominatim'] += 1
                validation_status = 'GEOCODE_FAILED'
            elif lat and lon:
                stats['geocoded'] += 1
                validation_status = 'GEOCODED_OK'
            else:
                stats['not_geocoded'] += 1
                validation_status = 'NO_GPS'

            print(f"  Geocode: {geo_source} -> lat={lat}, lon={lon}, commune={commune}".encode('ascii', 'replace').decode())
            print(f"  Validation status: {validation_status}".encode('ascii', 'replace').decode())

            # 4. Insertion
            try:
                c.execute('''
                    INSERT INTO places
                        (place_id, nom, nom_normalized, adresse, adresse_normalized,
                         telephone, telephone_normalized, telephone_raw, site_web,
                         note, nombre_avis, horaires, latitude, longitude,
                         google_maps_url, type_google, wilaya, wilaya_normalized,
                         commune, categorie_recherche, source, scrape_date,
                         status, name_status, name_source, recovery_date,
                         commune_source, commune_confidence, commune_updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    place_id, name_fr, nom_normalized, None, None, None, None, None, None,
                    None, None, None, lat, lon, None, None, wilaya, wilaya.lower(),
                    commune, categorie, 'MIPH_2025_SYNTH',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'active',
                    'VERIFIED', 'MIPH_2025_SYNTH', None,
                    geo_source if geo_source != 'REJECTED_POSTAL_ZERO' else 'MIPH_2025_SYNTH',
                    0.6 if commune else 0.0,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ))
                conn.commit()
                stats['imported'] += 1

                log_entry({'action': 'IMPORTED', 'pdf_id': pdf_id, 'place_id': place_id,
                          'nom': name_fr, 'wilaya': wilaya, 'postal_code': postal_code,
                          'latitude': lat if lat else '', 'longitude': lon if lon else '',
                          'commune': commune if commune else '', 'geocode_source': geo_source,
                          'validation_status': validation_status, 'duplicate_check': 'OK',
                          'phone_validation': '', 'website_validation': '', 'error_detail': ''})
                print(f"  RESULT: IMPORTED (id will be assigned)")

            except Exception as e:
                stats['errors'] += 1
                conn.rollback()
                log_entry({'action': 'ERROR_EXCEPTION', 'pdf_id': pdf_id, 'place_id': place_id,
                          'nom': name_fr, 'wilaya': wilaya, 'postal_code': postal_code,
                          'validation_status': 'EXCEPTION', 'error_detail': f'{type(e).__name__}: {e}'})
                print(f"  RESULT: ERROR - {type(e).__name__}: {e}")

    conn.close()
    return stats


def verify_synthetic(db_path: str = SYNTH_DB_PATH) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM places;')
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025_SYNTH';")
    synth_count = c.fetchone()[0]
    c.execute("SELECT id, place_id, nom, wilaya, latitude, longitude FROM places WHERE source = 'MIPH_2025_SYNTH';")
    synth_rows = c.fetchall()
    c.execute('PRAGMA integrity_check;')
    integrity = c.fetchone()[0]
    conn.close()
    return {
        'total_places': total,
        'synth_count': synth_count,
        'synth_entities': synth_rows,
        'integrity': integrity,
    }


def main():
    print('=' * 70)
    print('TEST SYNTHÉTIQUE PHASE 6.1.1 — CAS LIMITES')
    print('=' * 70)
    print(f'DB: {SYNTH_DB_PATH}')
    print(f'CSV: {SYNTH_CSV}')
    print(f'Log: {SYNTH_LOG}')
    print()

    # Premier passage
    print('>>> PREMIER PASSAGE <<<')
    stats1 = import_synthetic_entities(SYNTH_DB_PATH)

    print('\n' + '=' * 70)
    print('RÉSUMÉ 1ER PASSAGE')
    print('=' * 70)
    for k, v in stats1.items():
        print(f'  {k}: {v}')

    # Vérification
    print('\n>>> VÉRIFICATION APRÈS 1ER PASSAGE <<<')
    verify1 = verify_synthetic(SYNTH_DB_PATH)
    print(f'  Total places: {verify1["total_places"]}')
    print(f'  Entités synthétiques: {verify1["synth_count"]}')
    print(f'  Intégrité: {verify1["integrity"]}')
    for row in verify1['synth_entities']:
        print(f"    id={row[0]}, place_id={row[1]}, nom={row[2]}, wilaya={row[3]}, GPS=({row[4]},{row[5]})".encode('ascii', 'replace').decode())

    # Deuxième passage (test idempotence)
    print('\n>>> DEUXIÈME PASSAGE (test idempotence) <<<')
    stats2 = import_synthetic_entities(SYNTH_DB_PATH)

    print('\n' + '=' * 70)
    print('RÉSUMÉ 2E PASSAGE')
    print('=' * 70)
    for k, v in stats2.items():
        print(f'  {k}: {v}')

    # Vérification finale
    print('\n>>> VÉRIFICATION FINALE <<<')
    verify2 = verify_synthetic(SYNTH_DB_PATH)
    print(f'  Total places: {verify2["total_places"]}')
    print(f'  Entités synthétiques: {verify2["synth_count"]}')
    print(f'  Intégrité: {verify2["integrity"]}')
    for row in verify2['synth_entities']:
        print(f"    id={row[0]}, place_id={row[1]}, nom={row[2]}, wilaya={row[3]}, GPS=({row[4]},{row[5]})".encode('ascii', 'replace').decode())

    # Analyse résultats
    print('\n' + '=' * 70)
    print('ANALYSE DES RÉSULTATS ATTENDUS vs RÉELS')
    print('=' * 70)
    
    expected = {
        'SYNTH_001': 'IMPORTED (nouvelle entité valide)',
        'SYNTH_002': 'SKIP_DUPLICATE_ID (même place_id que SYNTH_001)',
        'SYNTH_003': 'REJECTED_POSTAL_ZERO (code_postal=0)',
        'SYNTH_004': 'IMPORTED (coordonnées valides attendues pour 16000 Alger)',
        'SYNTH_005': 'IMPORTED (même nom mais wilaya différente = entité distincte)',
        'SYNTH_006': 'IMPORTED (même nom mais wilaya différente = entité distincte)',
    }
    
    print("Entité | Attendu | Résultat 1er | Résultat 2e")
    print("-------|---------|--------------|------------")
    
    # Parse logs to get actual results
    with open(SYNTH_LOG, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        log_rows = list(reader)
    
    actions_by_pdf = {}
    for row in log_rows:
        pid = row['pdf_id']
        if pid not in actions_by_pdf:
            actions_by_pdf[pid] = []
        actions_by_pdf[pid].append(row['action'])
    
    for pdf_id, expected_result in expected.items():
        actions = actions_by_pdf.get(pdf_id, [])
        result1 = actions[0] if len(actions) > 0 else 'N/A'
        result2 = actions[1] if len(actions) > 1 else 'N/A'
        status = 'OK' if (result1 == expected_result.split(' ')[0] or 
                         (expected_result.startswith('IMPORTED') and result1 == 'IMPORTED') or
                         (expected_result.startswith('SKIP') and result1.startswith('SKIP')) or
                         (expected_result.startswith('REJECTED') and result1.startswith('SKIP'))) else 'MISMATCH'
        print(f"  {pdf_id} | {expected_result} | {result1} | {result2} [{status}]")

    print(f'\nLog détaillé: {SYNTH_LOG}')
    print(f'DB synthétique: {SYNTH_DB_PATH}')


if __name__ == '__main__':
    main()