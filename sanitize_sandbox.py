import os
import sys
import json
import hashlib
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

PROD_DB = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
SANDBOX_DB = r"D:\SANTE_DZ_EXPORTS\medizy_scraper_sandbox.db"
REPORTS_DIR = r"D:\SANTE_DZ_EXPORTS\reports"
COMMUNES_JSON = r"C:\SANTE_DZ_SCRAPER\communes_algerie_officielles.json"
VERIFICATION_REPORT = os.path.join(REPORTS_DIR, "sanitize_sandbox_verification.json")

def normalize_text(s):
    if not s:
        return ""
    s = unicodedata.normalize('NFKD', s)
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower().replace("'", "").replace("-", " ")

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def sanitize_sandbox():
    print(f"[{datetime.now().isoformat()}] DÉMARRAGE DE L'ASSAINISSEMENT SUR SANDBOX")
    print(f"Cible Sandbox : {SANDBOX_DB}")
    print(f"Production protégée (vérification seule) : {PROD_DB}")
    
    # 0. Vérification préliminaire de la production
    prod_sha_before = compute_sha256(PROD_DB)
    expected_prod_sha = "948fda84d6375b6b1dbd7ba822cdcfe09f7301f81f8779bc803e717b582c493d"
    assert prod_sha_before == expected_prod_sha, f"ALERTE : Base de production compromise avant démarrage ! ({prod_sha_before})"
    
    # Connexion RW sur Sandbox EXCLUSIVEMENT
    conn = sqlite3.connect(SANDBOX_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Initial audit stats on sandbox
    c.execute("SELECT COUNT(*) FROM places WHERE telephone = '0104346352' OR telephone_raw = '0104346352';")
    before_phones = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM places WHERE site_web LIKE '%fonts.gstatic.com%';")
    before_fonts_web = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM places WHERE site_web LIKE '%sante-dz.com%' OR site_web LIKE '%tibdz%';")
    before_external_web = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM places WHERE ROUND(latitude, 5) = 28.09487 AND ROUND(longitude, 5) = 1.66544;")
    before_centroid = c.fetchone()[0]
    
    print(f"Avant assainissement :")
    print(f"  - Téléphones 0104346352 : {before_phones}")
    print(f"  - Sites fonts.gstatic.com : {before_fonts_web}")
    print(f"  - Liens externes sante-dz/tibdz : {before_external_web}")
    print(f"  - Centroïdes nationaux (28.09487, 1.66544) : {before_centroid}")
    
    # 1. Ajout de la colonne geocoding_level si absente
    c.execute("PRAGMA table_info(places);")
    columns = [col["name"] for col in c.fetchall()]
    if "geocoding_level" not in columns:
        print("Ajout de la colonne geocoding_level dans places...")
        c.execute("ALTER TABLE places ADD COLUMN geocoding_level TEXT DEFAULT 'original_gps';")
        conn.commit()

    # 2. Consolidation des tables de référence dans la Sandbox
    # A. Mise à jour de la wilaya 57 (El Meghaier) si coordonnées nulles
    c.execute("""
        UPDATE wilayas 
        SET latitude = 34.354, longitude = 5.74 
        WHERE code = '57' AND (latitude IS NULL OR latitude = 0);
    """)
    conn.commit()
    
    # B. Chargement des coordonnées des communes depuis le référentiel officiel JSON
    if os.path.exists(COMMUNES_JSON):
        print(f"Enrichissement des coordonnées de communes depuis {COMMUNES_JSON}...")
        with open(COMMUNES_JSON, "r", encoding="utf-8") as f:
            communes_data = json.load(f)
            
        communes_enriched = 0
        for item in communes_data:
            geo = item.get("geo")
            if geo and geo.get("lat") and geo.get("lon"):
                try:
                    lat_val = float(geo["lat"])
                    lon_val = float(geo["lon"])
                    # Correspondance par nom_fr
                    name_en = item.get("name", {}).get("en")
                    zip_codes = item.get("zip_codes", [])
                    primary_zip = zip_codes[0] if zip_codes else None
                    
                    if primary_zip:
                        c.execute("""
                            UPDATE communes 
                            SET latitude = ?, longitude = ? 
                            WHERE zip_code = ? AND (latitude IS NULL OR latitude = 0);
                        """, (lat_val, lon_val, primary_zip))
                        if c.rowcount > 0:
                            communes_enriched += c.rowcount
                except Exception:
                    pass
        conn.commit()
        print(f"  Communes enrichies en coordonnées dans sandbox : {communes_enriched}")

    # Préparation du cache de géocodage de référence (Wilayas et Communes)
    c.execute("SELECT code, nom_fr, latitude, longitude FROM wilayas;")
    wilayas_ref = {}
    for r in c.fetchall():
        if r["latitude"] and r["longitude"]:
            norm_w = normalize_text(r["nom_fr"])
            wilayas_ref[norm_w] = (r["latitude"], r["longitude"], r["nom_fr"])
            
    # Alias manuels pour les wilayas spéciales
    wilayas_ref[normalize_text("El M'Ghair")] = (34.354, 5.74, "El Meghaier")
    wilayas_ref[normalize_text("El Meghaier")] = (34.354, 5.74, "El Meghaier")
    wilayas_ref[normalize_text("Bordj Bou Arreridj")] = wilayas_ref.get(normalize_text("Bordj Bou Arréridj"), (36.073, 4.761, "Bordj Bou Arréridj"))
    wilayas_ref[normalize_text("Béni Abbès")] = wilayas_ref.get(normalize_text("Béni Abbès"), (30.133, -2.167, "Béni Abbès"))
    
    # Cache communes
    c.execute("SELECT nom_fr, wilaya_code, latitude, longitude FROM communes WHERE latitude IS NOT NULL AND latitude != 0;")
    communes_ref = {}
    for r in c.fetchall():
        communes_ref[normalize_text(r["nom_fr"])] = (r["latitude"], r["longitude"])

    # 3. Traitement A : Nettoyage artefact Google Fonts
    print("Application du nettoyage Google Fonts...")
    c.execute("""
        UPDATE places 
        SET telephone = NULL, 
            telephone_normalized = NULL, 
            telephone_raw = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE telephone = '0104346352' OR telephone_raw = '0104346352';
    """)
    updated_phones_cnt = c.rowcount
    
    c.execute("""
        UPDATE places 
        SET site_web = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE site_web LIKE '%fonts.gstatic.com%';
    """)
    updated_fonts_web_cnt = c.rowcount
    conn.commit()
    print(f"  Téléphones réinitialisés : {updated_phones_cnt}")
    print(f"  Sites Google Fonts réinitialisés : {updated_fonts_web_cnt}")

    # 4. Traitement B : Nettoyage URLs résiduelles
    print("Application du nettoyage des liens externes résiduels...")
    c.execute("""
        UPDATE places 
        SET site_web = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE site_web LIKE '%sante-dz.com%' OR site_web LIKE '%tibdz%';
    """)
    updated_ext_web_cnt = c.rowcount
    conn.commit()
    print(f"  Liens externes réinitialisés : {updated_ext_web_cnt}")

    # 5. Traitement C : Recalcul des 90 centroïdes erronés
    print("Recalcul géospatial des 90 centroïdes erronés...")
    c.execute("""
        SELECT id, nom, wilaya, commune 
        FROM places 
        WHERE ROUND(latitude, 5) = 28.09487 AND ROUND(longitude, 5) = 1.66544;
    """)
    centroid_rows = c.fetchall()
    
    count_commune_centroid = 0
    count_wilaya_centroid = 0
    recalculated_details = []
    
    for row in centroid_rows:
        p_id = row["id"]
        p_nom = row["nom"]
        p_wilaya = row["wilaya"]
        p_commune = row["commune"]
        
        assigned_lat = None
        assigned_lon = None
        level = None
        
        # 1. Tentative par commune
        if p_commune and p_commune.strip():
            c_norm = normalize_text(p_commune)
            if c_norm in communes_ref:
                assigned_lat, assigned_lon = communes_ref[c_norm]
                level = "commune_centroid"
                count_commune_centroid += 1
                
        # 2. Rebut par wilaya chef-lieu
        if assigned_lat is None:
            w_norm = normalize_text(p_wilaya)
            if w_norm in wilayas_ref:
                assigned_lat, assigned_lon, canon_w = wilayas_ref[w_norm]
                level = "wilaya_centroid"
                count_wilaya_centroid += 1
            else:
                print(f"ATTENTION : Wilaya inconnue pour id={p_id}, wilaya={p_wilaya}")
                
        if assigned_lat is not None:
            c.execute("""
                UPDATE places 
                SET latitude = ?, 
                    longitude = ?, 
                    geocoding_level = ?, 
                    commune_source = 'centroid_remediation',
                    commune_updated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (assigned_lat, assigned_lon, level, p_id))
            recalculated_details.append({
                "id": p_id,
                "nom": p_nom,
                "wilaya": p_wilaya,
                "commune": p_commune,
                "new_latitude": assigned_lat,
                "new_longitude": assigned_lon,
                "geocoding_level": level
            })
            
    conn.commit()
    print(f"  Recalculs effectués : {len(recalculated_details)} / {len(centroid_rows)}")
    print(f"    - Niveau commune : {count_commune_centroid}")
    print(f"    - Niveau wilaya : {count_wilaya_centroid}")

    # 6. Vérifications finales sur la Sandbox
    print("Vérifications de contrôle post-assainissement...")
    c.execute("SELECT COUNT(*) FROM places WHERE telephone = '0104346352' OR telephone_raw = '0104346352';")
    after_phones = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM places WHERE site_web LIKE '%fonts.gstatic.com%';")
    after_fonts_web = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM places WHERE site_web LIKE '%sante-dz.com%' OR site_web LIKE '%tibdz%';")
    after_external_web = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM places WHERE ROUND(latitude, 5) = 28.09487 AND ROUND(longitude, 5) = 1.66544;")
    after_centroid = c.fetchone()[0]
    
    c.execute("PRAGMA integrity_check;")
    sandbox_integrity = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM places;")
    total_sandbox_places = c.fetchone()[0]
    
    c.execute("SELECT geocoding_level, COUNT(*) FROM places GROUP BY geocoding_level;")
    geocoding_distribution = dict(c.fetchall())
    
    conn.close()
    
    # 7. Contrôle absolu sur la base de production (inchangée)
    prod_sha_after = compute_sha256(PROD_DB)
    prod_unchanged = (prod_sha_after == expected_prod_sha)
    assert prod_unchanged, "ERREUR CRITIQUE : La base de production a été modifiée !"
    
    # 8. SHA256 de la sandbox après assainissement
    sandbox_sha_after = compute_sha256(SANDBOX_DB)
    sandbox_size_after = os.path.getsize(SANDBOX_DB)
    
    # Rapport comparatif
    report = {
        "execution_timestamp": datetime.now().isoformat(),
        "databases": {
            "production_master": {
                "path": PROD_DB,
                "sha256_initial": prod_sha_before,
                "sha256_final": prod_sha_after,
                "status": "STRICTEMENT_INCHANGEE_ET_PROTEGEE",
                "integrity": "ok"
            },
            "sandbox_remediated": {
                "path": SANDBOX_DB,
                "size_bytes": sandbox_size_after,
                "sha256_final": sandbox_sha_after,
                "integrity_check": sandbox_integrity,
                "total_records": total_sandbox_places
            }
        },
        "modifications_summary": {
            "google_fonts_artifact": {
                "initial_count": before_phones,
                "phones_cleared": updated_phones_cnt,
                "websites_cleared": updated_fonts_web_cnt,
                "remaining_phones": after_phones,
                "remaining_websites": after_fonts_web,
                "conformity": (after_phones == 0 and after_fonts_web == 0)
            },
            "external_links_artifact": {
                "initial_count": before_external_web,
                "websites_cleared": updated_ext_web_cnt,
                "remaining": after_external_web,
                "conformity": (after_external_web == 0)
            },
            "centroid_gps_remediation": {
                "initial_count": before_centroid,
                "recalculated_total": len(recalculated_details),
                "by_commune_centroid": count_commune_centroid,
                "by_wilaya_centroid": count_wilaya_centroid,
                "remaining_at_centroid_coords": after_centroid,
                "conformity": (after_centroid == 0)
            },
            "geocoding_level_distribution": geocoding_distribution
        },
        "sample_recalculated_records": recalculated_details[:10]
    }
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(VERIFICATION_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print(f"\n[SUCCÈS] Rapport de vérification sauvegardé dans : {VERIFICATION_REPORT}")
    return report

if __name__ == "__main__":
    rep = sanitize_sandbox()
    print("\nBILAN SYNTHÉTIQUE DE L'ASSAINISSEMENT :")
    print(f"  - Intégrité Sandbox : {rep['databases']['sandbox_remediated']['integrity_check']}")
    print(f"  - SHA-256 Sandbox : {rep['databases']['sandbox_remediated']['sha256_final']}")
    print(f"  - Production intacte : {rep['databases']['production_master']['status']}")
    print(f"  - Téléphones parasites restants : {rep['modifications_summary']['google_fonts_artifact']['remaining_phones']}")
    print(f"  - Sites Google Fonts restants : {rep['modifications_summary']['google_fonts_artifact']['remaining_websites']}")
    print(f"  - Liens externes restants : {rep['modifications_summary']['external_links_artifact']['remaining']}")
    print(f"  - Centroïdes nationaux restants : {rep['modifications_summary']['centroid_gps_remediation']['remaining_at_centroid_coords']}")
