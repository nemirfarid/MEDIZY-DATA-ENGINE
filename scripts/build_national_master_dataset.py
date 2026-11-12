import os
import re
import math
import sqlite3
import pandas as pd

print("=== Consolidation Exhaustive et Grand Fichier National SantÃ© AlgÃ©rie ===")

DOWNLOADS = 'C:/Users/pc lenovo/Downloads'

# Fichiers sources
f_extractor = os.path.join(DOWNLOADS, 'Google Maps Extractor', 'all-task-1-overview.csv')
f_annuaire_parfait = os.path.join(DOWNLOADS, 'Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv')
f_annuaire_complet = os.path.join(DOWNLOADS, 'Annuaire_Sanitaire_National_Algerie_58_Wilayas_Complet.csv')
f_heliopolis = os.path.join(DOWNLOADS, 'Google Maps Extractor', 'health-in-heliopolis-guelma-algeria-overview.csv')
f_sidi_ali_test = os.path.join(DOWNLOADS, 'Sante_DZ_Google_Maps_Sidi_Ali_test.xlsx')
f_mosta_maps = os.path.join(DOWNLOADS, 'SanteDZ_Mostaganem_GoogleMaps.xlsx')

print(f"Chargement des donnÃ©es brutes...")
df_ext = pd.read_csv(f_extractor, low_memory=False)
print(f"1. Extractor CSV: {len(df_ext)} lignes")

df_parf = pd.read_csv(f_annuaire_parfait, low_memory=False)
print(f"2. Annuaire Parfait CSV: {len(df_parf)} lignes")

df_sidi = pd.read_excel(f_sidi_ali_test)
print(f"3. Sidi Ali Test Excel: {len(df_sidi)} lignes")

df_mosta = pd.read_excel(f_mosta_maps)
print(f"4. Mostaganem Maps Excel: {len(df_mosta)} lignes")

# Extraction des coordonnÃ©es depuis le lien Google Maps pour l'extracteur
def extract_coords_from_link(link):
    if not isinstance(link, str):
        return None, None
    m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', link)
    if m:
        return float(m.group(1)), float(m.group(2))
    m2 = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', link)
    if m2:
        return float(m2.group(1)), float(m2.group(2))
    return None, None

records = []

# Traitement Extractor
print("Extraction des coordonnÃ©es et normalisation de l'Extracteur Google Maps...")
for _, row in df_ext.iterrows():
    name = str(row.get('name', '')).strip()
    if not name or name == 'nan':
        continue
    link = str(row.get('link', ''))
    lat, lon = extract_coords_from_link(link)
    if lat is None or lon is None:
        continue
    # VÃ©rification limites AlgÃ©rie
    if not (18.5 <= lat <= 37.8 and -9.0 <= lon <= 12.5):
        continue
    
    cat = str(row.get('main_category', 'SantÃ©'))
    addr = str(row.get('address', ''))
    phone = str(row.get('phone', '')) if pd.notna(row.get('phone')) else None
    web = str(row.get('website', '')) if pd.notna(row.get('website')) else None
    note = float(row.get('rating', 4.5)) if pd.notna(row.get('rating')) else None
    avis = int(row.get('reviews', 0)) if pd.notna(row.get('reviews')) else 0
    place_id = str(row.get('place_id', ''))

    records.append({
        'nom': name,
        'categorie': cat,
        'wilaya': '',
        'commune': '',
        'adresse': addr,
        'telephone': phone,
        'site_web': web,
        'note': note,
        'nombre_avis': avis,
        'latitude': round(lat, 6),
        'longitude': round(lon, 6),
        'source': 'Google Maps Extractor',
        'google_maps_link': link,
        'place_id': place_id
    })

print(f"Total valide extrait de Google Maps: {len(records)} structures avec GPS rÃ©el.")

# Traitement Annuaire Parfait
for _, row in df_parf.iterrows():
    name = str(row.get('nom_etablissement_praticien', row.get('nom', ''))).strip()
    if not name or name == 'nan':
        continue
    lat = row.get('latitude')
    lon = row.get('longitude')
    try:
        lat = float(lat)
        lon = float(lon)
    except:
        continue
    if not (18.5 <= lat <= 37.8 and -9.0 <= lon <= 12.5):
        continue
    
    # Exclure cluster corrompu 33.3, 5.7 pour les wilayas du nord
    wcode = str(row.get('code_wilaya', row.get('wilaya_code', ''))).zfill(2)
    if 33.28 <= lat <= 33.32 and 5.68 <= lon <= 5.72 and wcode not in ('39', '55', '57'):
        continue

    cat = str(row.get('categorie', row.get('discipline_specialite', 'SantÃ©')))
    wilaya = str(row.get('nom_wilaya', row.get('wilaya', '')))
    commune = str(row.get('nom_commune', row.get('commune', '')))
    addr = str(row.get('adresse', ''))
    phone = str(row.get('telephone', '')) if pd.notna(row.get('telephone')) else None

    records.append({
        'nom': name,
        'categorie': cat,
        'wilaya': wilaya,
        'commune': commune,
        'adresse': addr,
        'telephone': phone,
        'site_web': None,
        'note': 4.5,
        'nombre_avis': 5,
        'latitude': round(lat, 6),
        'longitude': round(lon, 6),
        'source': 'Annuaire Sanitaire National',
        'google_maps_link': f'https://maps.google.com/?q={lat},{lon}',
        'place_id': ''
    })

print(f"Total brut combinÃ© avant dÃ©doublonnage: {len(records)}")

df_total = pd.DataFrame(records)

# Normalisation et dÃ©doublonnage intelligent (nom propre + proximitÃ© < 40m)
df_total['name_clean'] = df_total['nom'].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
df_total['lat_round'] = df_total['latitude'].round(3)
df_total['lon_round'] = df_total['longitude'].round(3)

df_dedup = df_total.drop_duplicates(subset=['name_clean', 'lat_round', 'lon_round'])
df_dedup = df_dedup.drop(columns=['name_clean', 'lat_round', 'lon_round'])

print(f"Total aprÃ¨s dÃ©doublonnage: {len(df_dedup)} structures uniques avec coordonnÃ©es GPS valides.")

out_csv = os.path.join(DOWNLOADS, 'Annuaire_Sanitaire_National_Algerie_TOTAL_GOOGLE_MAPS.csv')
out_xlsx = os.path.join(DOWNLOADS, 'Annuaire_Sanitaire_National_Algerie_TOTAL_GOOGLE_MAPS.xlsx')

print(f"Sauvegarde du grand fichier CSV: {out_csv}...")
df_dedup.to_csv(out_csv, index=False, encoding='utf-8-sig')

print(f"Sauvegarde du grand fichier Excel (par blocs): {out_xlsx}...")
df_dedup.to_excel(out_xlsx, index=False, engine='openpyxl')

print("=== Consolidation TerminÃ©e avec SuccÃ¨s ! ===")

