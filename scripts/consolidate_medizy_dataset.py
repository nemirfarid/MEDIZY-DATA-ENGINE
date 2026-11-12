#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'audit, de fusion, de déduplication et de génération du fichier
consolidé pour Medizy à partir des données existantes et des nouveaux
fichiers extraits de Google Maps Extractor.
"""

import os
import re
import math
import sqlite3
import pandas as pd

# 1. Chemins des fichiers
DOWNLOADS_DIR = os.path.expanduser(r'~\Downloads')
EXTRACTOR_CSV = os.path.join(DOWNLOADS_DIR, 'Google Maps Extractor', 'all-task-1-overview.csv')
PARFAIT_CSV = os.path.join(DOWNLOADS_DIR, 'Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv')
OUTPUT_CSV = os.path.join(DOWNLOADS_DIR, 'Annuaire_Sanitaire_Medizy_Consolide_GPS.csv')
OUTPUT_XLSX = os.path.join(DOWNLOADS_DIR, 'Annuaire_Sanitaire_Medizy_Consolide_GPS.xlsx')

print("=== DEBUT DE L'ANALYSE ET CONSOLIDATION MEDIZY ===")
print(f"Source 1 (Actuel Medizy) : {PARFAIT_CSV}")
print(f"Source 2 (Nouveau Google Maps Extractor) : {EXTRACTOR_CSV}")

# 2. Référentiel des Wilayas
WILAYAS_58 = {
    '01': 'Adrar', '02': 'Chlef', '03': 'Laghouat', '04': 'Oum El Bouaghi',
    '05': 'Batna', '06': 'Béjaïa', '07': 'Biskra', '08': 'Béchar',
    '09': 'Blida', '10': 'Bouira', '11': 'Tamanrasset', '12': 'Tébessa',
    '13': 'Tlemcen', '14': 'Tiaret', '15': 'Tizi Ouzou', '16': 'Alger',
    '17': 'Djelfa', '18': 'Jijel', '19': 'Sétif', '20': 'Saïda',
    '21': 'Skikda', '22': 'Sidi Bel Abbès', '23': 'Annaba', '24': 'Guelma',
    '25': 'Constantine', '26': 'Médéa', '27': 'Mostaganem', '28': "M'Sila",
    '29': 'Mascara', '30': 'Ouargla', '31': 'Oran', '32': 'El Bayadh',
    '33': 'Illizi', '34': 'Bordj Bou Arréridj', '35': 'Boumerdès',
    '36': 'El Tarf', '37': 'Tindouf', '38': 'Tissemsilt', '39': 'El Oued',
    '40': 'Khenchela', '41': 'Souk Ahras', '42': 'Tipaza', '43': 'Mila',
    '44': 'Aïn Defla', '45': 'Naâma', '46': 'Aïn Témouchent', '47': 'Ghardaïa',
    '48': 'Relizane', '49': 'Timimoun', '50': 'Bordj Badji Mokhtar',
    '51': 'Ouled Djellal', '52': 'Béni Abbès', '53': 'In Salah',
    '54': 'In Guezzam', '55': 'Touggourt', '56': 'Djanet',
    '57': "El M'Ghair", '58': 'El Meniaa'
}

def clean_arabic_translit(text):
    if not text or pd.isna(text):
        return ""
    text = str(text).strip()
    return text

# Mappage des catégories Google Maps vers la nomenclature Medizy
CATEGORY_MAPPING = {
    'Pharmacie': ("Pharmacie d'Officine", "Officine Pharmaceutique"),
    'Medecin': ("Médecine Générale", "Médecin Généraliste"),
    'Cabinet medical': ("Médecine Générale", "Cabinet Médical"),
    'Cabinet dentaire': ("Chirurgie Dentaire", "Chirurgien-Dentiste"),
    'Dentiste': ("Chirurgie Dentaire", "Chirurgien-Dentiste"),
    'Clinique': ("Clinique Privée", "Clinique Médico-Chirurgicale"),
    'Hopital': ("Établissement Public", "Hôpital Public"),
    'Centre medical': ("Établissement Public", "Centre de Santé / Polyclinique"),
    "Laboratoire d'analyse medicale": ("Laboratoire d'analyses", "Laboratoire de Biologie Médicale"),
    'Gynecologue-obstetricien': ("Médecine Spécialisée", "Gynécologie - Obstétrique"),
    'Parapharmacie': ("Pharmacie d'Officine", "Parapharmacie"),
    'Pediatre': ("Médecine Spécialisée", "Pédiatrie"),
    'Opticien': ("Paramédical & Rééducation", "Optique Médicale"),
    'Cardiologue': ("Médecine Spécialisée", "Cardiologie"),
    'Medecin generaliste': ("Médecine Générale", "Médecin Généraliste"),
    'Ophtalmologiste': ("Médecine Spécialisée", "Ophtalmologie"),
    'Kinesitherapeute': ("Paramédical & Rééducation", "Kinésithérapie Motrice"),
    'Orthophoniste': ("Paramédical & Rééducation", "Orthophonie"),
    'Maison de naissance': ("Établissement Public", "Maternité"),
    'Centre de sante communautaire': ("Établissement Public", "Centre de Santé Communautaire"),
    'Dermatologue': ("Médecine Spécialisée", "Dermatologie"),
    'Chirurgien orthopediste': ("Médecine Spécialisée", "Chirurgie Orthopédique"),
    "Centre d'imagerie pour diagnostic medical": ("Centre d'Imagerie", "Imagerie Médicale & Radiologie"),
    'Dispensaire': ("Établissement Public", "Dispensaire / Salle de Soins"),
    'Gynecologue': ("Médecine Spécialisée", "Gynécologie - Obstétrique"),
    'Urologue': ("Médecine Spécialisée", "Urologie"),
    'Gastro-enterologue': ("Médecine Spécialisée", "Gastro-entérologie"),
    'Pneumologue': ("Médecine Spécialisée", "Pneumologie"),
    'Radiologue': ("Centre d'Imagerie", "Radiologie & Scanner"),
    'Psychiatre': ("Médecine Spécialisée", "Psychiatrie"),
    'Departement de sante publique': ("Établissement Public", "Direction de la Santé et de la Population (DSP)"),
    'Clinique chirurgicale': ("Clinique Privée", "Clinique Chirurgicale"),
    'Medecin de famille': ("Médecine Générale", "Médecine de Famille"),
    'Maison de sante': ("Établissement Public", "Maison de Santé"),
    'Clinique ORL': ("Clinique Privée", "Clinique ORL"),
    'Groupe medical': ("Médecine Spécialisée", "Groupe Médical"),
    'Centre de reeducation': ("Paramédical & Rééducation", "Rééducation Fonctionnelle"),
    'Neurologue': ("Médecine Spécialisée", "Neurologie"),
    'Chirurgien': ("Médecine Spécialisée", "Chirurgie Générale"),
    'Centre de dialyse': ("Clinique Privée", "Centre d'Hémodialyse"),
    'Institut de formation en soins infirmiers': ("Paramédical & Rééducation", "Institut de Formation Paramédicale"),
    'Psychotherapeute': ("Médecine Spécialisée", "Psychothérapie"),
    'Nutritionniste': ("Paramédical & Rééducation", "Nutrition & Diététique"),
    'Interniste': ("Médecine Spécialisée", "Médecine Interne"),
    'Service de soins a domicile': ("Paramédical & Rééducation", "Soins Infirmiers à Domicile"),
    'Clinique accessible sans rendez-vous': ("Clinique Privée", "Clinique Sans Rendez-Vous"),
    'Clinique orthopedique': ("Clinique Privée", "Clinique Orthopédique"),
    'Clinique ophtalmologique': ("Clinique Privée", "Clinique Ophtalmologique"),
    'Service hospitalier': ("Établissement Public", "Service Hospitalier"),
    'Endocrinologue': ("Médecine Spécialisée", "Endocrinologie - Diabétologie"),
    'Clinique specialisee': ("Clinique Privée", "Clinique Spécialisée"),
    'Centre de diagnostic': ("Centre d'Imagerie", "Centre de Diagnostic"),
    'Rhumatologue': ("Médecine Spécialisée", "Rhumatologie"),
    'Optometriste': ("Paramédical & Rééducation", "Optométrie"),
    'Service ambulancier': ("Établissement Public", "Ambulance & Transport Sanitaire"),
    'Centre de radiologie': ("Centre d'Imagerie", "Centre de Radiologie"),
    'Allergologue': ("Médecine Spécialisée", "Allergologie"),
    'Néphrologue': ("Médecine Spécialisée", "Néphrologie"),
    'Nephrologue': ("Médecine Spécialisée", "Néphrologie"),
    'Oncologue': ("Médecine Spécialisée", "Oncologie"),
    'Pediatrie': ("Médecine Spécialisée", "Pédiatrie"),
    'Psychologue': ("Paramédical & Rééducation", "Psychologie Clinique")
}

def normalize_str(s):
    if not s or pd.isna(s):
        return ""
    s = str(s).lower()
    for src, dst in [('é', 'e'), ('è', 'e'), ('ê', 'e'), ('ë', 'e'), ('à', 'a'), ('â', 'a'), ('ï', 'i'), ('î', 'i'), ('ô', 'o'), ('ö', 'o'), ('ù', 'u'), ('û', 'u'), ('ç', 'c')]:
        s = s.replace(src, dst)
    return re.sub(r'[^a-z0-9]', '', s)

# Distance haversine en mètres
def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2.0)**2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

# 3. Chargement du fichier actuel Medizy
print("\n--- Étape 1 : Chargement de l'annuaire actuel Medizy ---")
df_parfait = pd.read_csv(PARFAIT_CSV, sep=';', encoding='cp1252')
df_parfait.columns = [c.replace('ï»¿', '').replace('﻿', '').strip() for c in df_parfait.columns]
print(f"Fiches existantes chargées : {len(df_parfait)}")

# Suppression immédiate de toute ligne sans GPS valide dans l'existant
df_parfait = df_parfait[df_parfait['latitude'].notna() & df_parfait['longitude'].notna()].copy()
df_parfait['latitude'] = pd.to_numeric(df_parfait['latitude'], errors='coerce')
df_parfait['longitude'] = pd.to_numeric(df_parfait['longitude'], errors='coerce')
df_parfait = df_parfait[
    (df_parfait['latitude'] >= 18.0) & (df_parfait['latitude'] <= 38.0) &
    (df_parfait['longitude'] >= -9.0) & (df_parfait['longitude'] <= 12.0)
].copy()
print(f"Fiches existantes avec GPS valide Algérie : {len(df_parfait)}")

# Préparation de l'index de déduplication (grille spatiale + téléphone)
existing_phones = set()
spatial_grid = {}

for idx, row in df_parfait.iterrows():
    tel = str(row['telephone']) if pd.notna(row['telephone']) else ""
    digits = re.sub(r'\D', '', tel)
    if len(digits) >= 8:
        existing_phones.add(digits[-8:])
    
    lat = row['latitude']
    lon = row['longitude']
    grid_key = (round(lat, 2), round(lon, 2))
    norm_name = normalize_str(row['nom_etablissement_praticien'])
    spatial_grid.setdefault(grid_key, []).append((lat, lon, norm_name))

# 4. Chargement des nouveaux fichiers Google Maps Extractor
print("\n--- Étape 2 : Chargement et filtrage des nouveaux fichiers Google Maps ---")
df_new_raw = pd.read_csv(EXTRACTOR_CSV)
print(f"Lignes brutes dans all-task-1-overview.csv : {len(df_new_raw)}")

# Extraction coordonnées GPS depuis le lien Google Maps
gps_pattern = re.compile(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)')
new_lats = []
new_lons = []
for link in df_new_raw['link'].astype(str):
    m = gps_pattern.search(link)
    if m:
        new_lats.append(float(m.group(1)))
        new_lons.append(float(m.group(2)))
    else:
        new_lats.append(None)
        new_lons.append(None)

df_new_raw['lat_extracted'] = new_lats
df_new_raw['lon_extracted'] = new_lons

# ÉLIMINATION STRICTE : Ceux qui n'ont pas de coordonnées GPS (ou hors Algérie)
initial_count = len(df_new_raw)
df_new_raw = df_new_raw[df_new_raw['lat_extracted'].notna() & df_new_raw['lon_extracted'].notna()].copy()
df_new_raw = df_new_raw[
    (df_new_raw['lat_extracted'] >= 18.0) & (df_new_raw['lat_extracted'] <= 38.0) &
    (df_new_raw['lon_extracted'] >= -9.0) & (df_new_raw['lon_extracted'] <= 12.0)
].copy()
eliminated_gps = initial_count - len(df_new_raw)
print(f"Fiches éliminées car sans coordonnées GPS ou hors Algérie : {eliminated_gps}")
print(f"Fiches conservées avec GPS valide : {len(df_new_raw)}")

# Filtrage par catégorie médicale
df_new_health = df_new_raw[df_new_raw['main_category'].isin(CATEGORY_MAPPING.keys())].copy()
non_health_count = len(df_new_raw) - len(df_new_health)
print(f"Fiches non-médicales éliminées (salons, coiffure, cosmétique, etc.) : {non_health_count}")
print(f"Fiches médicales qualifiées retenues : {len(df_new_health)}")

# 5. Déduplication des nouvelles fiches par rapport à l'existant Medizy
print("\n--- Étape 3 : Déduplication intelligente par rapport à Medizy existant ---")

# Dictionnaire de correspondance wilaya depuis la query Google Maps
# e.g., 'health in heliopolis, guelma, algeria'
query_wilaya_cache = {}
def extract_wilaya_commune(query_str, address_str):
    q = str(query_str).lower().replace('health in', '').replace(', algeria', '').strip()
    parts = [p.strip() for p in q.split(',') if p.strip()]
    commune_found = parts[0].title() if len(parts) > 0 else "Indéterminée"
    wilaya_found = parts[1].title() if len(parts) > 1 else commune_found

    # Résolution code wilaya
    wilaya_norm = normalize_str(wilaya_found)
    matched_code = '16' # défaut Alger si inconnu
    matched_name = 'Alger'
    for code, name in WILAYAS_58.items():
        if normalize_str(name) == wilaya_norm or wilaya_norm in normalize_str(name):
            matched_code = code
            matched_name = name
            break
            
    # Vérification dans l'adresse (code postal 5 chiffres)
    addr = str(address_str)
    zip_match = re.search(r'\b(\d{2})\d{3}\b', addr)
    if zip_match:
        code_cand = zip_match.group(1)
        if code_cand in WILAYAS_58:
            matched_code = code_cand
            matched_name = WILAYAS_58[code_cand]

    return matched_code, matched_name, commune_found

new_records_to_add = []
duplicates_found = 0

for idx, row in df_new_health.iterrows():
    name = str(row['name']).strip()
    norm_name = normalize_str(name)
    lat = row['lat_extracted']
    lon = row['lon_extracted']
    tel = str(row['phone']) if pd.notna(row['phone']) else ""
    digits = re.sub(r'\D', '', tel)

    # 1. Vérification téléphone
    is_dup = False
    if len(digits) >= 8 and digits[-8:] in existing_phones:
        is_dup = True

    # 2. Vérification spatiale et nom (distance < 20m ou même nom < 50m)
    if not is_dup:
        grid_key = (round(lat, 2), round(lon, 2))
        candidates = spatial_grid.get(grid_key, [])
        for c_lat, c_lon, c_name in candidates:
            dist = haversine_m(lat, lon, c_lat, c_lon)
            if dist < 15: # Même emplacement exact
                is_dup = True
                break
            if dist < 60 and (norm_name == c_name or (len(norm_name) > 6 and norm_name in c_name)):
                is_dup = True
                break

    if is_dup:
        duplicates_found += 1
    else:
        # Fiche unique validée ! On l'ajoute
        existing_phones.add(digits[-8:] if len(digits) >= 8 else "")
        grid_key = (round(lat, 2), round(lon, 2))
        spatial_grid.setdefault(grid_key, []).append((lat, lon, norm_name))

        cat_main = row['main_category']
        medizy_cat, medizy_disc = CATEGORY_MAPPING.get(cat_main, ("Médecine Spécialisée", cat_main))
        wcode, wname, cname = extract_wilaya_commune(row['query'], row['address'])

        # Formattage adresse
        addr = str(row['address']).strip() if pd.notna(row['address']) else f"{cname}, {wname}"
        horaires = str(row['workday_timing']).strip() if pd.notna(row['workday_timing']) else "Non spécifié"
        if horaires.lower() == 'nan':
            horaires = "Non spécifié"
            
        rating = f"Note: {row['rating']}/5 ({int(row['reviews'])} avis)" if pd.notna(row['rating']) and pd.notna(row['reviews']) else "Google Maps Vérifié"

        new_records_to_add.append({
            'code_wilaya': int(wcode),
            'nom_wilaya': wname,
            'nom_daira': cname,
            'nom_commune': cname,
            'categorie': medizy_cat,
            'discipline_specialite': medizy_disc,
            'nom_etablissement_praticien': name,
            'adresse': addr,
            'telephone': tel if tel and str(tel).lower() != 'nan' else "",
            'horaires': horaires,
            'latitude': lat,
            'longitude': lon,
            'coordonnees_gps': f"{lat:.4f}, {lon:.4f}",
            'statut_remarques': rating,
            'source': "Google Maps Extractor 2026"
        })

print(f"Doublons identifiés et écartés : {duplicates_found}")
print(f"Nouvelles structures uniques qualifiées à intégrer : {len(new_records_to_add)}")

# 6. Consolidation finale avec l'existant
print("\n--- Étape 4 : Génération du fichier consolidé ---")
df_new_records = pd.DataFrame(new_records_to_add)

# Harmonisation des colonnes de l'annuaire existant
# Renommage de la première colonne si nécessaire (BOM UTF-8)
df_parfait.columns = [c.replace('﻿', '') for c in df_parfait.columns]

# Liste des colonnes cibles standardisées Medizy
target_cols = [
    'id', 'code_wilaya', 'nom_wilaya', 'nom_daira', 'nom_commune',
    'categorie', 'discipline_specialite', 'nom_etablissement_praticien',
    'adresse', 'telephone', 'horaires', 'latitude', 'longitude',
    'coordonnees_gps', 'statut_remarques', 'source'
]

# Attribution des nouveaux IDs séquentiels
start_id = df_parfait['id'].max() + 1
df_new_records['id'] = range(start_id, start_id + len(df_new_records))

# Réordonnancement des colonnes
df_new_records = df_new_records[target_cols]
df_parfait_clean = df_parfait[target_cols].copy()

# Concaténation finale
df_consolidated = pd.concat([df_parfait_clean, df_new_records], ignore_index=True)

# Vérification finale d'intégrité GPS
df_consolidated = df_consolidated[df_consolidated['latitude'].notna() & df_consolidated['longitude'].notna()]
df_consolidated['code_wilaya'] = df_consolidated['code_wilaya'].astype(int)

print(f"TOTAL FICHES DANS LE FICHIER CONSOLIDÉ : {len(df_consolidated)}")
print(f"  - Fiches initiales Medizy : {len(df_parfait_clean)}")
print(f"  - Nouvelles fiches ajoutées : {len(df_new_records)}")
print(f"  - Pourcentage sans GPS : 0.00% (100% géolocalisées)")

# 7. Sauvegarde du nouveau fichier
print("\n--- Étape 5 : Écriture des fichiers de sortie ---")
df_consolidated.to_csv(OUTPUT_CSV, sep=';', index=False, encoding='utf-8-sig')
print(f"Fichier CSV généré avec succès : {OUTPUT_CSV}")

# Sauvegarde d'un échantillon ou du complet en Excel
# (Excel complet de ~55k lignes tient largement sous la limite de 1M lignes de xlsx)
print("Génération du fichier Excel (.xlsx)...")
df_consolidated.to_excel(OUTPUT_XLSX, index=False, engine='openpyxl')
print(f"Fichier Excel généré avec succès : {OUTPUT_XLSX}")

print("\n=== CONSOLIDATION TERMINÉE AVEC SUCCÈS ===")
