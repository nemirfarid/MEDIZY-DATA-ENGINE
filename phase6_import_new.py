"""
Phase 6 — Import 24 nouvelles entités MIPH PDF vers la DB

Imports the 24 entities from miph_crossref_new.csv that are not present in the DB.
Geocodes missing GPS via Nominatim using postal_code + wilaya.
Marque source = 'MIPH_2025', name_status = 'VERIFIED', name_source = 'MIPH_2025'
"""

import sqlite3
import csv
import time
import urllib.request
import urllib.parse
import json
import os
from datetime import datetime

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
MIPH_CSV = r'D:\SANTE_DZ_EXPORTS\miph_crossref_new.csv'

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


def geocode_postal(wilaya_code: int, postal_code: str):
    """Use Nominatim to geocode via postal code + Alger region, Algeria."""
    if not postal_code or str(postal_code).strip() in ('0', '00000', ''):
        return None, None, None

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
        time.sleep(1)  # Respect Nominatim rate limit (1 req/sec)

        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            addr = data[0].get('address', {})
            commune = addr.get('town') or addr.get('village') or addr.get('city') or None
            return lat, lon, commune
    except Exception as e:
        print(f"    Géocodage échoué pour {postal_code}: {e}")

    return None, None, None


def normalize_arabic(text: str) -> str:
    """Clean up encoding artifacts from CSV parsing."""
    if not text:
        return ''
    # Replace artifacts
    text = text.replace('D?centralis', '')
    text = text.replace('D?centralis', '')
    text = text.strip()
    return text


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if any of these 24 entities already exist (by normalized name)
    imported = 0
    skipped = 0
    geocoded = 0

    with open(MIPH_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name_fr = row['etab_fr'].strip()
            name_ar = normalize_arabic(row.get('etab_ar', ''))

            # Normalize name for duplicate check
            nom_normalized = name_fr.lower().strip()
            if 'établissement public hospitalier' in nom_normalized:
                nom_normalized = nom_normalized.replace('établissement public hospitalier', '').strip()
            nom_normalized = nom_normalized.replace('(', '').replace(')', '').strip()

            # Check if already exists
            c.execute('SELECT id FROM places WHERE nom_normalized LIKE ? OR nom LIKE ?', 
                      (f'%{nom_normalized}%', f'%{name_fr}%'))
            if c.fetchone():
                print(f"  SKIP (déjà existant): {name_fr}")
                skipped += 1
                continue

            wilaya = row['wilaya'].strip()
            wilaya_code = int(row['wilaya_code'])
            postal_code = row['code_postal'].strip()
            type_etab = row['type_etab'].strip()
            categorie = MIPH_TYPE_TO_CATEGORIE.get(type_etab, 'Structure')

            # Geocode via Nominatim
            lat, lon, commune = geocode_postal(wilaya_code, postal_code)
            if lat and lon:
                geocoded += 1
                print(f"  Géocodé: {name_fr} → ({lat:.4f}, {lon:.4f})")
            else:
                print(f"  Pas de GPS pour {name_fr} (code postal: {postal_code})")

            # Build place_id
            place_id = f"miph_{row['pdf_id']}"

            # Insert
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
                place_id,
                name_fr,             # nom
                nom_normalized,       # nom_normalized
                None,                 # adresse
                None,                 # adresse_normalized
                None,                 # telephone
                None,                 # telephone_normalized
                None,                 # telephone_raw
                None,                 # site_web
                None,                 # note
                None,                 # nombre_avis
                None,                 # horaires
                lat,                  # latitude
                lon,                  # longitude
                None,                 # google_maps_url
                None,                 # type_google
                wilaya,               # wilaya
                wilaya.lower(),       # wilaya_normalized
                commune,              # commune
                categorie,            # categorie_recherche
                'MIPH_2025',          # source
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # scrape_date
                'active',             # status
                'VERIFIED',           # name_status
                'MIPH_2025',          # name_source
                None,                 # recovery_date
                'MIPH_2025',          # commune_source
                0.6 if commune else 0.0,  # commune_confidence
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # commune_updated_at
            ))
            imported += 1
            conn.commit()
            time.sleep(1.5)  # Rate limit for Nominatim

    conn.close()
    print(f"\n=== Import terminé ===")
    print(f"  Importés: {imported}")
    print(f"  Skippés (déjà existants): {skipped}")
    print(f"  Géocodés via Nominatim: {geocoded}")
    print(f"  Non-géocodés (GPS null): {imported - geocoded}")


if __name__ == '__main__':
    main()
