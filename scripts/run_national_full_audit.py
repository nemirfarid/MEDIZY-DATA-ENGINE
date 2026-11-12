import sqlite3
import math
import sys

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Blacklist of non-medical categories / commercial junk
NON_HEALTH = set([
    'magasin de produits de beaute', 'magasin de meubles', 'magasin de vetements',
    'fabricant de produits en ceramique', 'centre de loisirs', 'code postal',
    'nan', 'centre d\'information', 'etablissement d\'enseignement professionnel',
    'entreprise de cosmetique', 'salon de coiffure', 'coiffeur', 'salle de gym',
    'supermarche', 'epicerie', 'restaurant', 'cafe', 'hotel', 'banque'
])

CLEAN_MAPPING = {
    'cabinet medical': 'Médecin',
    'cabinet médical': 'Médecin',
    'medecin': 'Médecin',
    'médecin': 'Médecin',
    'medecin generaliste': 'Médecin Généraliste',
    'médecin généraliste': 'Médecin Généraliste',
    'interniste': 'Médecine Interne',
    'medecin specialiste de la douleur': 'Médecin',
    'medecin specialiste de la gestion de la douleur': 'Médecin',
    'medecin specialiste de la fertilite': 'Gynécologue',
    'gynecologue-obstetricien': 'Gynécologue',
    'gynécologue': 'Gynécologue',
    'maison de naissance': 'Maternité / Gynécologue',
    'cabinet dentaire': 'Dentiste',
    'dentiste': 'Dentiste',
    'chirurgie dentaire': 'Dentiste',
    'hopital': 'Hôpital & Urgences',
    'hôpital': 'Hôpital & Urgences',
    'hopital prive': 'Clinique Privée',
    'hopital psychiatrique': 'Hôpital Spécialisé',
    'service hospitalier': 'Hôpital & Urgences',
    'clinique médicale': 'Clinique',
    'clinique medicale': 'Clinique',
    'clinique': 'Clinique',
    'hôpital & clinique': 'Clinique',
    'clinique chirurgicale': 'Clinique Chirurgicale',
    'clinique accessible sans rendez-vous': 'Clinique / Urgences',
    'laboratoire d\'analyse medicale': 'Laboratoire d\'Analyses',
    'laboratoire d\'analyses': 'Laboratoire d\'Analyses',
    'laboratoire': 'Laboratoire d\'Analyses',
    'centre d\'imagerie pour diagnostic medical': 'Centre d\'Imagerie & Radiologie',
    'imagerie / radio': 'Centre d\'Imagerie & Radiologie',
    'service de mammographie': 'Centre d\'Imagerie & Radiologie',
    'pediatre': 'Pédiatre',
    'pédiatre': 'Pédiatre',
    'ophtalmologiste': 'Ophtalmologue',
    'ophtalmologue': 'Ophtalmologue',
    'kinesitherapeute': 'Kinésithérapeute',
    'kinésithérapeute': 'Kinésithérapeute',
    'dispensaire': 'Polyclinique / Dispensaire',
    'centre de sante communautaire': 'Polyclinique / Dispensaire',
    'centre medical': 'Centre Médical',
    'centre médical': 'Centre Médical',
    'centre medical public': 'Centre de Santé Public',
    'maison de sante': 'Centre de Santé',
    'groupe medical': 'Centre Médical',
    'centre de soins ambulatoires': 'Centre de Santé',
    'pharmacie': 'Pharmacie',
    'pharmacie bio': 'Pharmacie',
    'drugstore': 'Pharmacie',
    'parapharmacie': 'Parapharmacie',
    'cardiologue': 'Cardiologue',
    'dermatologue': 'Dermatologue',
    'urologue': 'Urologue',
    'rhumatologue': 'Rhumatologue',
    'pneumologue': 'Pneumologue',
    'conseiller sante': 'Professionnel de Santé',
    'service de la sante au travail': 'Santé au Travail',
    'service de sante mentale': 'Santé Mentale',
    'centre de reeducation': 'Centre de Rééducation',
    'fournisseur d\'equipements medicaux': 'Matériel Médical',
    'magasin de materiel medical': 'Matériel Médical',
    'praticien de medecine alternative': 'Médecine Alternative',
    'departement de sante publique': 'Structure de Santé Publique',
    'service de depistage des drogues': 'Laboratoire / Dépistage',
    'centre de planning familial': 'Centre de Santé',
    'institut de formation en soins infirmiers': 'Formation Paramédicale',
    'mutuelle de sante': 'Organisme de Santé',
    'orthophoniste': 'Orthophoniste'
}

def clean_category(cat):
    if not cat:
        return 'Médecin'
    cat_lower = str(cat).lower().strip()
    if cat_lower in NON_HEALTH:
        return None
    return CLEAN_MAPPING.get(cat_lower, str(cat).strip())

def process_all_wilayas():
    print("=== STARTING FULL NATIONAL AUDIT & CONSOLIDATION (58 WILAYAS) ===")
    
    conn_scraper = sqlite3.connect('medizy_scraper.db')
    c_scraper = conn_scraper.cursor()
    
    # 1. Load all official wilayas & communes
    c_scraper.execute("SELECT code, nom_fr FROM wilayas ORDER BY CAST(code AS INTEGER)")
    wilayas = c_scraper.fetchall()
    
    c_scraper.execute("SELECT wilaya_code, nom_fr, nom_ar, latitude, longitude FROM communes")
    all_communes = c_scraper.fetchall()
    
    communes_by_wilaya = {}
    for w_code, c_fr, c_ar, lat, lon in all_communes:
        code_str = str(w_code).zfill(2)
        if code_str not in communes_by_wilaya:
            communes_by_wilaya[code_str] = []
        communes_by_wilaya[code_str].append((c_fr, c_ar, lat, lon))
        
    print(f"Loaded {len(wilayas)} wilayas and {len(all_communes)} official communes.")
    
    conn_target = sqlite3.connect('assets/data/sante_dz_bundled.db')
    c_target = conn_target.cursor()
    
    # 2. Iterate Wilaya by Wilaya
    national_summary = []
    
    for w_code, w_name in wilayas:
        w_code_str = str(w_code).zfill(2)
        
        # Load places from scraper for this wilaya
        c_scraper.execute("""
            SELECT id, nom, commune, categorie_recherche, type_google, latitude, longitude, telephone, adresse, site_web, note, nombre_avis, google_maps_url
            FROM places 
            WHERE wilaya = ? OR wilaya_normalized = ?
        """, (w_name, w_name.lower()))
        scraper_places = c_scraper.fetchall()
        
        # Ingest missing genuine places from scraper
        c_target.execute("SELECT place_id, nom, latitude, longitude FROM facilities WHERE wilaya_code = ?", (w_code_str,))
        existing_target = c_target.fetchall()
        existing_names = set((r[1] or '').strip().lower() for r in existing_target)
        existing_places = set(r[0] for r in existing_target if r[0])
        
        inserted_from_scraper = 0
        for sp in scraper_places:
            p_id = str(sp[0])
            p_name = (sp[1] or '').strip()
            p_comm = sp[2] or w_name
            cat_candidate = sp[3] or sp[4] or 'Médecin'
            p_cat = clean_category(cat_candidate)
            p_lat = sp[5]
            p_lon = sp[6]
            p_phone = sp[7]
            p_addr = sp[8]
            p_web = sp[9]
            p_rate = sp[10]
            p_reviews = sp[11]
            p_url = sp[12]
            
            if not p_cat or not p_lat or not p_lon:
                continue
            
            # Algerian geographical bounding box (approximate)
            if not (18.5 <= p_lat <= 38.0 and -9.0 <= p_lon <= 12.5):
                continue
            
            # Check duplicate
            if p_id in existing_places or p_name.lower() in existing_names:
                continue
                
            c_target.execute("""
                INSERT INTO facilities (
                    place_id, nom, categorie, wilaya, wilaya_code, commune,
                    adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_id, p_name, p_cat, w_name, w_code_str, p_comm,
                p_addr, p_phone, p_web, p_rate, p_reviews, p_lat, p_lon, 'Google Maps / OSM Officiel'
            ))
            existing_places.add(p_id)
            existing_names.add(p_name.lower())
            inserted_from_scraper += 1
            
        # Re-fetch all facilities for this wilaya to normalize communes & categories
        c_target.execute("""
            SELECT id, nom, commune, categorie, latitude, longitude 
            FROM facilities 
            WHERE wilaya_code = ? OR wilaya = ?
        """, (w_code_str, w_name))
        current_facs = c_target.fetchall()
        
        w_communes = communes_by_wilaya.get(w_code_str, [])
        
        purged_junk = 0
        normalized_count = 0
        commune_stats = {}
        category_stats = {}
        
        for f_id, f_nom, f_comm, f_cat, f_lat, f_lon in current_facs:
            # Check category validity
            final_cat = clean_category(f_cat)
            if not final_cat:
                c_target.execute("DELETE FROM facilities WHERE id = ?", (f_id,))
                purged_junk += 1
                continue
            
            # Filter obvious water / out of algeria coordinates
            if not f_lat or not f_lon or not (18.5 <= f_lat <= 38.0 and -9.0 <= f_lon <= 12.5):
                c_target.execute("DELETE FROM facilities WHERE id = ?", (f_id,))
                purged_junk += 1
                continue
                
            # Assign nearest official commune
            best_commune = w_name
            if w_communes:
                min_dist = 999999.0
                for c_fr, c_ar, c_lat, c_lon in w_communes:
                    if f_comm and f_comm.lower().strip() == c_fr.lower().strip():
                        best_commune = c_fr
                        min_dist = 0
                        break
                    if c_lat and c_lon and f_lat and f_lon:
                        d = haversine(f_lat, f_lon, c_lat, c_lon)
                        if d < min_dist:
                            min_dist = d
                            best_commune = c_fr
            
            c_target.execute("""
                UPDATE facilities 
                SET commune = ?, categorie = ?, wilaya = ?, wilaya_code = ? 
                WHERE id = ?
            """, (best_commune, final_cat, w_name, w_code_str, f_id))
            
            normalized_count += 1
            commune_stats[best_commune] = commune_stats.get(best_commune, 0) + 1
            category_stats[final_cat] = category_stats.get(final_cat, 0) + 1

        conn_target.commit()
        print(f"Wilaya {w_code_str} ({w_name}): {normalized_count} valid facilities across {len(commune_stats)} communes (+{inserted_from_scraper} imported, {purged_junk} purged).")
        national_summary.append({
            'code': w_code_str,
            'name': w_name,
            'total': normalized_count,
            'communes_count': len(commune_stats)
        })

    # 3. Final National Database Sync
    print("\n--- REBUILDING FULL NATIONAL SPATIAL & SEARCH INDICES ---")
    c_target.execute("DELETE FROM facilities_rtree")
    c_target.execute("""
        INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
        SELECT id, latitude, latitude, longitude, longitude FROM facilities
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    conn_target.commit()
    
    c_target.execute("INSERT INTO facilities_fts(facilities_fts) VALUES('rebuild')")
    conn_target.commit()
    
    c_target.execute("SELECT COUNT(*), COUNT(DISTINCT wilaya_code), COUNT(DISTINCT commune) FROM facilities")
    grand_total, total_w, total_c = c_target.fetchone()
    print(f"\n=======================================================")
    print(f"NATIONAL INTEGRATION 100% COMPLETE:")
    print(f"Total Authentic Health Facilities : {grand_total}")
    print(f"Total Wilayas Covered              : {total_w} / 58")
    print(f"Total Communes Covered             : {total_c}")
    print(f"=======================================================")

if __name__ == '__main__':
    process_all_wilayas()
