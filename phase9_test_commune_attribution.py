#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 9.2 - Test attribution des communes pour les 140 entrées OSM (READ-ONLY simulation).
Utilise la table officielle 'communes' et 'wilayas'.
"""
import sqlite3
import math

PROD = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0 # Rayon terrestre en km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def main():
    with sqlite3.connect(PROD) as conn:
        cur = conn.cursor()
        
        # 1. Charger les wilayas et leurs codes
        cur.execute("SELECT code, nom_fr FROM wilayas")
        wilaya_code_map = {nom.lower().replace(" ", "").replace("'", ""): code for code, nom in cur.fetchall()}
        
        # 2. Charger les communes officielles par wilaya_code
        cur.execute("SELECT wilaya_code, nom_fr, latitude, longitude FROM communes WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        communes_by_code = {}
        for wcode, cnom, clat, clon in cur.fetchall():
            communes_by_code.setdefault(wcode, []).append((cnom, clat, clon))
            
        print(f"Codes wilayas charges : {len(wilaya_code_map)}")
        print(f"Wilayas avec communes reference : {len(communes_by_code)}")
        
        # 3. Récupérer les 140 entrées OSM
        cur.execute("""
            SELECT id, place_id, nom, wilaya, latitude, longitude 
            FROM places 
            WHERE source LIKE 'osm_overpass%'
        """)
        osm_rows = cur.fetchall()
        print(f"Entrees OSM a analyser : {len(osm_rows)}")
        
        matches = []
        no_matches = []
        
        for pid, place_id, nom, wil, lat, lon in osm_rows:
            norm_wil = wil.lower().replace(" ", "").replace("'", "").replace("é", "e").replace("è", "e")
            # Chercher le code
            wcode = None
            for kw, code in wilaya_code_map.items():
                if norm_wil in kw or kw in norm_wil:
                    wcode = code
                    break
                    
            if not wcode or wcode not in communes_by_code:
                no_matches.append((pid, nom, wil, "Code wilaya non trouve"))
                continue
                
            # Trouver la commune la plus proche
            candidates = communes_by_code[wcode]
            best_com = None
            min_dist = float("inf")
            for cnom, clat, clon in candidates:
                d = haversine_km(lat, lon, clat, clon)
                if d < min_dist:
                    min_dist = d
                    best_com = cnom
                    
            confidence = "HIGH" if min_dist <= 15.0 else ("MEDIUM" if min_dist <= 50.0 else "LOW")
            matches.append((pid, nom, wil, best_com, round(min_dist, 2), confidence))
            
        print(f"\nResultats du recoupement geographique :")
        print(f"  * Correspondances trouvees : {len(matches)}/{len(osm_rows)} ({len(matches)*100.0/len(osm_rows):.1f}%)")
        print(f"  * Non attribuees : {len(no_matches)}")
        
        high_cnt = sum(1 for m in matches if m[5] == "HIGH")
        med_cnt = sum(1 for m in matches if m[5] == "MEDIUM")
        low_cnt = sum(1 for m in matches if m[5] == "LOW")
        print(f"  * Confiance HIGH (<= 15 km) : {high_cnt}")
        print(f"  * Confiance MEDIUM (15-50 km) : {med_cnt}")
        print(f"  * Confiance LOW (> 50 km) : {low_cnt}")
        
        print("\nExemples de correspondances simulees :")
        for m in matches[:10]:
            print(f"  [ID {m[0]}] {m[1][:30]} | {m[2]} -> Commune: {m[3]} (dist: {m[4]} km, conf: {m[5]})")

if __name__ == "__main__":
    main()
