"""
Test des cas limites pour l'import MIPH sécurisé
- code_postal = 0
- Échecs Nominatim
- Entrées déjà existantes
"""

import sqlite3
import tempfile
import os
import sys

# Ajouter le répertoire au path pour importer le module sécurisé
sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')

from phase6_import_new_secured import (
    validate_coordinates,
    validate_phone,
    validate_website,
    build_nom_normalized,
    check_business_duplicate,
    geocode_postal,
    ALGERIA_BOUNDS
)

def test_validate_coordinates():
    print('=== TEST validate_coordinates ===')
    # Valides (Alger)
    assert validate_coordinates(36.7372, 3.0865) == (True, 'OK'), 'Alger devrait être valide'
    # Valides (Tamanrasset - sud)
    assert validate_coordinates(22.7903, 5.5292) == (True, 'OK'), 'Tamanrasset devrait être valide'
    # Invalides - hors bornes
    assert validate_coordinates(50.0, 3.0)[0] == False, 'Latitude 50 devrait être invalide'
    assert validate_coordinates(20.0, -20.0)[0] == False, 'Longitude -20 devrait être invalide'
    # Null
    assert validate_coordinates(None, 3.0)[0] == False, 'NULL lat devrait être invalide'
    assert validate_coordinates(36.0, None)[0] == False, 'NULL lon devrait être invalide'
    print('  OK: Tous les tests de coordonnées passent')

def test_validate_phone():
    print('=== TEST validate_phone ===')
    # Valides
    assert validate_phone('0555123456') == (True, 'OK'), 'Mobile Algérie valide'
    assert validate_phone('0661123456') == (True, 'OK'), 'Mobile Algérie valide'
    assert validate_phone('0770123456') == (True, 'OK'), 'Mobile Algérie valide'
    assert validate_phone('0982123456') == (True, 'OK'), 'Mobile Algérie valide'
    assert validate_phone('021123456') == (True, 'OK_LANDLINE'), 'Fixe 9 chiffres'
    assert validate_phone('0211234567') == (True, 'OK_LANDLINE'), 'Fixe 10 chiffres'
    # Invalides
    assert validate_phone('')[0] == False, 'Vide invalide'
    assert validate_phone(None)[0] == False, 'None invalide'
    assert validate_phone('123')[0] == False, 'Trop court invalide'
    assert validate_phone('0104346352')[0] == False, 'Format suspect (template) invalide'
    print('  OK: Tous les tests de téléphone passent')

def test_validate_website():
    print('=== TEST validate_website ===')
    # Valides
    assert validate_website('https://example.com') == (True, 'OK'), 'Site valide'
    assert validate_website('http://hopital-alger.dz') == (True, 'OK'), 'HTTP valide'
    # Invalides - CDN/templates
    assert validate_website('https://fonts.gstatic.com/s/roboto/v20/KFOmCnqEu92Fr1Mu4mxK.woff2')[0] == False, 'fonts.gstatic.com bloqué'
    assert validate_website('https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js')[0] == False, 'googleapis.com bloqué'
    assert validate_website('https://cdnjs.cloudflare.com/ajax/libs/lodash/4.17.21/lodash.min.js')[0] == False, 'cloudflare bloqué'
    # Invalides - format
    assert validate_website('')[0] == False, 'Vide invalide'
    assert validate_website(None)[0] == False, 'None invalide'
    assert validate_website('not-a-url')[0] == False, 'Sans schéma invalide'
    print('  OK: Tous les tests de site web passent')

def test_build_nom_normalized():
    print('=== TEST build_nom_normalized ===')
    assert build_nom_normalized('Etablissement Public Hospitalier Ibn Sina') == 'ibn sina'
    assert build_nom_normalized('Hôpital Mustapha Pacha') == 'mustapha pacha'
    assert build_nom_normalized('Centre de Santé Bouira') == 'bouira'
    assert build_nom_normalized('Clinique El Amel (Alger)') == 'el amel alger'
    assert build_nom_normalized('EPSP Adrar') == 'adrar'
    print('  OK: Normalisation noms correcte')

def test_geocode_postal_zero():
    print('=== TEST geocode_postal avec code_postal=0 ===')
    # Ce test ne fait pas d'appel réseau réel, on teste la logique de rejet
    lat, lon, commune, source = geocode_postal(16, '0')
    assert lat is None and lon is None and commune is None
    assert source == 'REJECTED_POSTAL_ZERO', f'Expected REJECTED_POSTAL_ZERO, got {source}'
    
    lat, lon, commune, source = geocode_postal(16, '00000')
    assert source == 'REJECTED_POSTAL_ZERO'
    
    lat, lon, commune, source = geocode_postal(16, '')
    assert source == 'REJECTED_POSTAL_ZERO'
    
    lat, lon, commune, source = geocode_postal(16, None)
    assert source == 'REJECTED_POSTAL_ZERO'
    print('  OK: code_postal=0 correctement rejeté sans appel réseau')

def test_check_business_duplicate():
    print('=== TEST check_business_duplicate ===')
    # Créer une base temporaire
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        conn = sqlite3.connect(tmp_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE places (
                id INTEGER PRIMARY KEY,
                nom_normalized TEXT,
                wilaya_normalized TEXT,
                categorie_recherche TEXT
            )
        ''')
        c.execute("INSERT INTO places (id, nom_normalized, wilaya_normalized, categorie_recherche) VALUES (1, 'ibn sina', 'alger', 'hôpital')")
        c.execute("INSERT INTO places (id, nom_normalized, wilaya_normalized, categorie_recherche) VALUES (2, 'mustapha pacha', 'alger', 'hôpital')")
        conn.commit()
        
        # Test détection doublon
        existing = check_business_duplicate(c, 'ibn sina', 'Alger', 'hôpital')
        assert existing == 1, f'Devrait trouver id=1, trouvé {existing}'
        
        # Test pas de doublon (différente wilaya)
        existing = check_business_duplicate(c, 'ibn sina', 'Oran', 'hôpital')
        assert existing is None, 'Ne devrait pas trouver (wilaya différente)'
        
        # Test pas de doublon (différente catégorie)
        existing = check_business_duplicate(c, 'ibn sina', 'Alger', 'clinique')
        assert existing is None, 'Ne devrait pas trouver (catégorie différente)'
        
        conn.close()
        print('  OK: Détection doublons métier correcte')
    finally:
        os.unlink(tmp_path)

def test_algeria_bounds():
    print('=== TEST ALGERIA_BOUNDS ===')
    # Points connus en Algérie
    alger = (36.7372, 3.0865)
    oran = (35.6969, -0.6331)
    constantine = (36.3650, 6.6147)
    tamanrasset = (22.7903, 5.5292)
    djanet = (24.5569, 9.4731)
    
    for name, (lat, lon) in [('Alger', alger), ('Oran', oran), ('Constantine', constantine), 
                              ('Tamanrasset', tamanrasset), ('Djanet', djanet)]:
        valid, reason = validate_coordinates(lat, lon)
        assert valid, f'{name} ({lat},{lon}) devrait être valide: {reason}'
    
    # Points hors Algérie
    paris = (48.8566, 2.3522)
    madrid = (40.4168, -3.7038)
    for name, (lat, lon) in [('Paris', paris), ('Madrid', madrid)]:
        valid, reason = validate_coordinates(lat, lon)
        assert not valid, f'{name} ({lat},{lon}) devrait être invalide: {reason}'
    
    print('  OK: Bornes Algérie correctes')

if __name__ == '__main__':
    print('TESTS CAS LIMITES - PHASE 6.1 IMPORT MIPH SÉCURISÉ')
    print('=' * 60)
    
    test_validate_coordinates()
    test_validate_phone()
    test_validate_website()
    test_build_nom_normalized()
    test_geocode_postal_zero()
    test_check_business_duplicate()
    test_algeria_bounds()
    
    print('=' * 60)
    print('TOUS LES TESTS CAS LIMITES PASSENT OK')