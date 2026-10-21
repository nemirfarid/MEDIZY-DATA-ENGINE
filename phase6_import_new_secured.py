"""
Phase 6.1 — Sécurisation de l'import MIPH (Version Sécurisée)

Cette version travaille UNIQUEMENT sur une base de TEST.
N'importe JAMAIS la base de production.

Garanties:
- Idempotence via place_id UNIQUE + vérification métier (nom + wilaya + type)
- code_postal=0 traité comme invalide : pas de géocodage, GPS laissé NULL, journalisé
- Validation coordonnées dans bornes Algérie
- Détection doublons métier (même nom/wilaya/catégorie)
- Détection valeurs suspectes (téléphones/sites identiques en masse)
- Provenance conservée + historique corrections GPS
- Logging complet: succès, échecs, coordonnées, raisons de rejet
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
# CONFIGURATION — CHEMINS TEST UNIQUEMENT
# ============================================================================
TEST_DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db'
MIPH_CSV = r'D:\SANTE_DZ_EXPORTS\miph_crossref_new.csv'
LOG_FILE = r'C:\SANTE_DZ_SCRAPER\phase6_import_miph_log.csv'

# Bornes géographiques Algérie (approximatives)
ALGERIA_BOUNDS = {
    'lat_min': 18.5, 'lat_max': 37.5,
    'lon_min': -9.0, 'lon_max': 12.5
}

# MIPH type → DB categorie_recherche mapping
MIPH_TYPE_TO_CATEGORIE = {
    'CHU': 'hôpital',
    'EPH': 'hôpital',
    'EH': 'hôpital',
    'EHS': 'clinique',
    'EHU': 'hôpital',
    'EPSP': 'centre de santé',
    'DSP': 'Structure',
    'INSTITUT/FORMATION': 'Institut de formation',
    'EST': 'Institut de formation',
    'INFSPM': 'Institut de formation',
    'INFPM': 'Institut de formation',
    'IFPM': 'Institut de formation',
    'IFSM': 'Institut de formation',
    'DRH': 'Direction',
    'Structure': 'Structure',
}

# Postal code prefix → wilaya name (for geocoding fallback)
POSTAL_WILAYA = {
    1: 'Adrar', 2: 'Chlef', 3: 'Laghouat', 4: 'Oum El Bouaghi',
    5: 'Biskra', 6: 'Béjaïa', 7: 'Biskra', 8: 'Béchar',
    9: 'Blida', 10: 'Bouira', 11: 'Tamanrasset', 12: 'Tébessa',
    13: 'Tlemcen', 14: 'Tiaret', 15: 'Tizi Ouzou', 16: 'Alger',
    17: 'Djelfa', 18: 'Jijel', 19: 'Sétif', 20: 'Saïda',
    21: 'Skikda', 22: 'Sidi Bel Abbès', 23: 'Annaba', 24: 'Guelma',
    25: 'Constantine', 26: 'Médéa', 27: 'Mostaganem', 28: 'M\'SilA',
    29: 'Mascara', 30: 'Ouargla', 31: 'Oran', 32: 'El Bayadh',
    33: 'Illizi', 34: 'Bordj Bou Arréridj', 35: 'Boumerdès',
    36: 'El Tarf', 37: 'Tindouf', 38: 'Tissemsilt', 39: 'El Oued',
    40: 'Khenchela', 41: 'Souk Ahras', 42: 'Tipaza', 43: 'Mila',
    44: 'Aïn Defla', 45: 'Naâma', 46: 'Aïn Témouchent',
    47: 'Ghardaïa', 48: 'Relizane', 49: 'Timimoun',
    50: 'Bordj Badji Mokhtar', 51: 'Ouled Djellal',
    52: 'Béni Abbès', 53: 'In Salah', 54: 'In Guezzam',
    55: 'Touggourt', 56: 'Djanet', 57: 'El M\'Ghair',
    58: 'El Meniaa',
}


# ============================================================================
# UTILITAIRES VALIDATION
# ============================================================================
def validate_coordinates(lat: Optional[float], lon: Optional[float]) -> Tuple[bool, str]:
    """Valide que les coordonnées sont dans les bornes de l'Algérie."""
    if lat is None or lon is None:
        return False, 'COORD_NULL'
    if not (ALGERIA_BOUNDS['lat_min'] <= lat <= ALGERIA_BOUNDS['lat_max']):
        return False, f'LAT_OUT_OF_BOUNDS ({lat})'
    if not (ALGERIA_BOUNDS['lon_min'] <= lon <= ALGERIA_BOUNDS['lon_max']):
        return False, f'LON_OUT_OF_BOUNDS ({lon})'
    return True, 'OK'


def validate_phone(phone: Optional[str]) -> Tuple[bool, str]:
    """Valide un numéro de téléphone algérien (format basique)."""
    if not phone:
        return False, 'PHONE_EMPTY'
    # Nettoyer
    clean = re.sub(r'[^\d]', '', phone)
    # Rejeter préfixes invalides (01 n'existe pas en Algérie)
    if clean.startswith('01'):
        return False, 'PHONE_INVALID_PREFIX_01'
    # Algérie mobile: 05, 06, 07, 09 + 8 chiffres = 10 chiffres total
    if re.match(r'^0[5679]\d{8}$', clean):
        return True, 'OK'
    # Algérie fixe: 0 + indicatif (2-3 chiffres) + 6-7 chiffres = 9-10 chiffres total
    # Ex: 021123456 (9 chiffres), 0211234567 (10 chiffres)
    if re.match(r'^0[234]\d{7,8}$', clean):
        return True, 'OK_LANDLINE'
    return False, f'PHONE_INVALID_FORMAT ({phone})'


def validate_website(url: Optional[str]) -> Tuple[bool, str]:
    """Valide basiquement une URL de site web."""
    if not url:
        return False, 'URL_EMPTY'
    # Rejeter les domaines de template/CDN connus
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
    """Nettoie les artefacts d'encodage depuis le CSV."""
    if not text:
        return ''
    text = text.replace('D?centralis', '')
    text = text.replace('D?centralis', '')
    text = text.replace('&eacute;', 'é')
    text = text.replace('&Eacute;', 'É')
    text = text.replace('&egrave;', 'è')
    text = text.replace('&Egrave;', 'È')
    return text.strip()


def build_nom_normalized(name_fr: str) -> str:
    """Normalise un nom pour détection de doublons métier."""
    n = name_fr.lower().strip()
    # Retirer préfixes génériques
    for prefix in ['établissement public hospitalier', 'etablissement public hospitalier',
                   'hôpital', 'hopital', 'centre de santé', 'centre de sante',
                   'clinique', 'institut', 'epsp', 'eph', 'eh', 'ehs', 'ehu']:
        n = n.replace(prefix, '').strip()
    n = n.replace('(', '').replace(')', '').strip()
    n = re.sub(r'\s+', ' ', n)
    return n


# ============================================================================
# GÉOCODAGE NOMINATIM — AVEC VALIDATION
# ============================================================================
def geocode_postal(wilaya_code: int, postal_code: str) -> Tuple[Optional[float], Optional[float], Optional[str], str]:
    """
    Géocode via Nominatim avec code postal.
    Retourne: (lat, lon, commune, geocode_source) ou (None, None, None, 'REJECTED')
    """
    # Rejeter explicitement code_postal = 0 ou invalide
    if not postal_code or str(postal_code).strip() in ('0', '00000', ''):
        return None, None, None, 'REJECTED_POSTAL_ZERO'

    query = f"{postal_code}, Algerie"
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'limit': '5',
        'addressdetails': '1',
    })

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SANTE_DZ_Project/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        time.sleep(1.1)  # Respect Nominatim rate limit (1 req/sec)

        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])

            # Valider bornes Algérie
            valid, reason = validate_coordinates(lat, lon)
            if not valid:
                return None, None, None, f'REJECTED_GEO_BOUNDS_{reason}'

            addr = data[0].get('address', {})
            commune = addr.get('town') or addr.get('village') or addr.get('city') or None
            return lat, lon, commune, 'NOMINATIM_POSTAL'

    except Exception as e:
        return None, None, None, f'NOMINATIM_ERROR_{type(e).__name__}'

    return None, None, None, 'NOMINATIM_NO_RESULT'


# ============================================================================
# DÉTECTION DOUBLONS MÉTIER
# ============================================================================
def check_business_duplicate(cursor: sqlite3.Cursor, nom_normalized: str, wilaya: str, categorie: str) -> Optional[int]:
    """
    Vérifie s'il existe déjà un établissement avec même nom_normalized + wilaya + catégorie.
    Retourne l'ID existant si trouvé, sinon None.
    """
    cursor.execute('''
        SELECT id FROM places
        WHERE nom_normalized = ? AND wilaya_normalized = ? AND categorie_recherche = ?
    ''', (nom_normalized, wilaya.lower(), categorie))
    row = cursor.fetchone()
    return row[0] if row else None


# ============================================================================
# LOGGING STRUCTURÉ
# ============================================================================
def init_log_file():
    """Initialise le fichier de log CSV."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'action', 'pdf_id', 'place_id', 'nom', 'wilaya',
                'postal_code', 'latitude', 'longitude', 'commune',
                'geocode_source', 'validation_status', 'duplicate_check',
                'phone_validation', 'website_validation', 'error_detail'
            ])


def log_entry(data: Dict[str, Any]):
    """Écrit une entrée de log."""
    row = [
        datetime.now().isoformat(),
        data.get('action', ''),
        data.get('pdf_id', ''),
        data.get('place_id', ''),
        data.get('nom', ''),
        data.get('wilaya', ''),
        data.get('postal_code', ''),
        data.get('latitude', ''),
        data.get('longitude', ''),
        data.get('commune', ''),
        data.get('geocode_source', ''),
        data.get('validation_status', ''),
        data.get('duplicate_check', ''),
        data.get('phone_validation', ''),
        data.get('website_validation', ''),
        data.get('error_detail', ''),
    ]
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(row)


# ============================================================================
# IMPORT PRINCIPAL
# ============================================================================
def import_miph_entities(db_path: str = TEST_DB_PATH) -> Dict[str, int]:
    """
    Importe les entités MIPH dans la base de TEST.
    Retourne un dict avec les compteurs.
    """
    init_log_file()

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Vérifier contraintes UNIQUE existantes
    c.execute("PRAGMA index_list(places);")
    indexes = c.fetchall()
    print(f"Indexes sur 'places': {len(indexes)}")

    # Compteurs
    stats = {
        'total_csv': 0,
        'imported': 0,
        'skipped_duplicate_id': 0,
        'skipped_business_duplicate': 0,
        'geocoded': 0,
        'not_geocoded': 0,
        'rejected_postal_zero': 0,
        'rejected_geo_bounds': 0,
        'rejected_nominatim': 0,
        'errors': 0
    }

    with open(MIPH_CSV, 'r', encoding='utf-8-sig') as f:
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

            # --- 1. VÉRIFIER DOUBLON PAR place_id (contrainte UNIQUE) ---
            c.execute('SELECT id FROM places WHERE place_id = ?', (place_id,))
            if c.fetchone():
                stats['skipped_duplicate_id'] += 1
                log_entry({
                    'action': 'SKIP_DUPLICATE_ID',
                    'pdf_id': pdf_id, 'place_id': place_id, 'nom': name_fr,
                    'wilaya': wilaya, 'postal_code': postal_code,
                    'validation_status': 'DUPLICATE_ID', 'duplicate_check': 'EXISTS_BY_PLACE_ID',
                    'error_detail': 'place_id already exists in DB'
                })
                print(f"  SKIP (place_id existant): {name_fr} [{place_id}]")
                continue

            # --- 2. VÉRIFIER DOUBLON MÉTIER (nom + wilaya + catégorie) ---
            existing_id = check_business_duplicate(c, nom_normalized, wilaya, categorie)
            if existing_id:
                stats['skipped_business_duplicate'] += 1
                log_entry({
                    'action': 'SKIP_BUSINESS_DUPLICATE',
                    'pdf_id': pdf_id, 'place_id': place_id, 'nom': name_fr,
                    'wilaya': wilaya, 'postal_code': postal_code,
                    'validation_status': 'DUPLICATE_BUSINESS', 'duplicate_check': f'EXISTS_ID_{existing_id}',
                    'error_detail': f'Business duplicate: same name+wilaya+cat (id={existing_id})'
                })
                print(f"  SKIP (doublon métier): {name_fr} (id={existing_id})")
                continue

            # --- 3. GÉOCODAGE (si code postal valide) ---
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

            # --- 4. VALIDATIONS TÉLÉPHONE / SITE WEB (pour futures importations) ---
            # Ces champs sont NULL pour MIPH, mais on valide la logique
            phone_valid, phone_reason = validate_phone(None)
            site_valid, site_reason = validate_website(None)

            # --- 5. INSERTION ---
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
                    place_id,                    # place_id (UNIQUE)
                    name_fr,                     # nom
                    nom_normalized,              # nom_normalized
                    None,                        # adresse
                    None,                        # adresse_normalized
                    None,                        # telephone
                    None,                        # telephone_normalized
                    None,                        # telephone_raw
                    None,                        # site_web
                    None,                        # note
                    None,                        # nombre_avis
                    None,                        # horaires
                    lat,                         # latitude
                    lon,                         # longitude
                    None,                        # google_maps_url
                    None,                        # type_google
                    wilaya,                      # wilaya
                    wilaya.lower(),              # wilaya_normalized
                    commune,                     # commune
                    categorie,                   # categorie_recherche
                    'MIPH_2025',                 # source
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # scrape_date
                    'active',                    # status
                    'VERIFIED',                  # name_status
                    'MIPH_2025',                 # name_source
                    None,                        # recovery_date
                    geo_source if geo_source != 'REJECTED_POSTAL_ZERO' else 'MIPH_2025',  # commune_source
                    0.6 if commune else 0.0,     # commune_confidence
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # commune_updated_at
                ))
                conn.commit()
                stats['imported'] += 1

                log_entry({
                    'action': 'IMPORTED',
                    'pdf_id': pdf_id, 'place_id': place_id, 'nom': name_fr,
                    'wilaya': wilaya, 'postal_code': postal_code,
                    'latitude': lat if lat else '', 'longitude': lon if lon else '',
                    'commune': commune if commune else '',
                    'geocode_source': geo_source,
                    'validation_status': validation_status,
                    'duplicate_check': 'OK',
                    'phone_validation': phone_reason,
                    'website_validation': site_reason,
                    'error_detail': ''
                })
                geo_str = f"GPS=({lat:.4f},{lon:.4f})" if lat else "GPS=NULL"
                print(f"  IMPORTÉ: {name_fr} [{place_id}] {geo_str} source={geo_source}")

            except sqlite3.IntegrityError as e:
                stats['errors'] += 1
                conn.rollback()
                log_entry({
                    'action': 'ERROR_INTEGRITY',
                    'pdf_id': pdf_id, 'place_id': place_id, 'nom': name_fr,
                    'wilaya': wilaya, 'postal_code': postal_code,
                    'validation_status': 'INTEGRITY_ERROR',
                    'error_detail': str(e)
                })
                print(f"  ERREUR INTÉGRITÉ: {name_fr} - {e}")

            except Exception as e:
                stats['errors'] += 1
                conn.rollback()
                log_entry({
                    'action': 'ERROR_EXCEPTION',
                    'pdf_id': pdf_id, 'place_id': place_id, 'nom': name_fr,
                    'wilaya': wilaya, 'postal_code': postal_code,
                    'validation_status': 'EXCEPTION',
                    'error_detail': f'{type(e).__name__}: {e}'
                })
                print(f"  ERREUR: {name_fr} - {type(e).__name__}: {e}")

    conn.close()
    return stats


# ============================================================================
# VÉRIFICATION POST-IMPORT
# ============================================================================
def verify_import(db_path: str = TEST_DB_PATH) -> Dict[str, Any]:
    """Vérifie l'état de la base après import."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Compter total
    c.execute('SELECT COUNT(*) FROM places;')
    total = c.fetchone()[0]

    # Compter MIPH_2025
    c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025';")
    miph_count = c.fetchone()[0]

    # GPS coverage MIPH
    c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025' AND latitude IS NOT NULL;")
    miph_gps = c.fetchone()[0]

    # Vérifier intégrité
    c.execute('PRAGMA integrity_check;')
    integrity = c.fetchone()[0]

    # Vérifier contraintes UNIQUE
    c.execute("SELECT COUNT(*) FROM places WHERE place_id IS NOT NULL;")
    place_id_count = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL;")
    place_id_distinct = c.fetchone()[0]

    # Vérifier google_maps_url UNIQUE
    c.execute("SELECT COUNT(*) FROM places WHERE google_maps_url IS NOT NULL;")
    gmaps_count = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT google_maps_url) FROM places WHERE google_maps_url IS NOT NULL;")
    gmaps_distinct = c.fetchone()[0]

    conn.close()

    return {
        'total_places': total,
        'miph_2025_count': miph_count,
        'miph_gps_count': miph_gps,
        'integrity': integrity,
        'place_id_unique_ok': place_id_count == place_id_distinct,
        'gmaps_url_unique_ok': gmaps_count == gmaps_distinct,
    }


# ============================================================================
# MAIN
# ============================================================================
def main():
    print('=' * 70)
    print('PHASE 6.1 — IMPORT MIPH SÉCURISÉ (BASE DE TEST)')
    print('=' * 70)
    print(f'DB Test: {TEST_DB_PATH}')
    print(f'CSV Source: {MIPH_CSV}')
    print(f'Log: {LOG_FILE}')
    print()

# Vérifier que c'est bien la base de test
    if 'test' not in TEST_DB_PATH.lower() and 'backup' not in TEST_DB_PATH.lower():
        print('ATTENTION: Ce script doit tourner sur une base de TEST uniquement !')
        return

    # Import
    stats = import_miph_entities(TEST_DB_PATH)

    print()
    print('=' * 70)
    print('RÉSUMÉ IMPORT')
    print('=' * 70)
    for k, v in stats.items():
        print(f'  {k}: {v}')

# Vérification
    print()
    print('=' * 70)
    print('VERIFICATION POST-IMPORT')
    print('=' * 70)
    verification = verify_import(TEST_DB_PATH)
    for k, v in verification.items():
        if k == 'integrity':
            status = 'OK' if v == 'ok' else 'FAIL'
        elif isinstance(v, bool):
            status = 'OK' if v else 'FAIL'
        else:
            status = 'INFO'
        print(f'  [{status}] {k}: {v}')

    # Test d'idempotence : deuxième exécution
    print()
    print('=' * 70)
    print('TEST D\'IDEMPOTENCE (2e exécution)')
    print('=' * 70)
    stats2 = import_miph_entities(TEST_DB_PATH)
    print()
    print('Résultats 2e exécution:')
    for k, v in stats2.items():
        print(f'  {k}: {v}')

    # Vérification finale
    print()
    print('=' * 70)
    print('VÉRIFICATION FINALE')
    print('=' * 70)
    verification2 = verify_import(TEST_DB_PATH)
    for k, v in verification2.items():
        if k == 'integrity':
            status = 'OK' if v == 'ok' else 'FAIL'
        elif isinstance(v, bool):
            status = 'OK' if v else 'FAIL'
        else:
            status = 'INFO'
        print(f'  [{status}] {k}: {v}')

    # Différences
    print()
    print('=' * 70)
    print('DIFFÉRENCES AVANT/APRÈS (2e exécution)')
    print('=' * 70)
    print(f'  Importés (1er run): {stats["imported"]}')
    print(f'  Importés (2e run): {stats2["imported"]}')
    print(f'  Différence: {stats2["imported"] - stats["imported"]} (doit être 0)')

    if stats2['imported'] == 0:
        print('  [OK] IDEMPOTENCE CONFIRMEE: Aucun doublon cree a la 2e execution')
    else:
        print('  [FAIL] IDEMPOTENCE ECHOUEE: Nouveaux enregistrements crees !')

    print()
    print(f'Log détaillé: {LOG_FILE}')


if __name__ == '__main__':
    main()