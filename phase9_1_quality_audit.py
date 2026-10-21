#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 9.1 - Comprehensive Quality & Integrity Audit of Consolidated Production Database.
Database: C:\SANTE_DZ_SCRAPER\medizy_scraper.db
"""
import sqlite3
import hashlib
import json
import os
import sys

PROD = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
REPORT = r"C:\SANTE_DZ_SCRAPER\phase9_1_quality_audit.txt"

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def run_audit():
    lines = []
    lines.append("=" * 70)
    lines.append("SANTÉ DZ / MEDIZY — PHASE 9.1 AUDIT DE QUALITÉ ET D'INTÉGRITÉ")
    lines.append("=" * 70)
    
    sha_prod = sha256_file(PROD)
    lines.append(f"Fichier : {PROD}")
    lines.append(f"Taille : {os.path.getsize(PROD):,} octets")
    lines.append(f"SHA-256 : {sha_prod}")
    
    with sqlite3.connect(PROD) as conn:
        cur = conn.cursor()
        
        # 1. Intégrité SQLite
        cur.execute("PRAGMA integrity_check")
        integ = cur.fetchone()[0]
        lines.append(f"Intégrité SQLite : {integ}")
        
        # 2. Structure des tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        lines.append(f"Tables présentes ({len(tables)}) : {', '.join(tables)}")
        
        # 3. Compte global
        cur.execute("SELECT COUNT(*) FROM places")
        total_places = cur.fetchone()[0]
        lines.append(f"\nTotal établissements (places) : {total_places}")
        
        # 4. Répartition par source
        lines.append("\n--- Répartition par source ---")
        cur.execute("""
            SELECT 
                CASE 
                    WHEN source LIKE 'osm_overpass%' THEN 'OpenStreetMap (Overpass)'
                    WHEN source LIKE 'geoalgeria%' THEN 'GeoAlgeria'
                    WHEN source = 'MIPH_2025' THEN 'MIPH 2025 (Ministère)'
                    ELSE source
                END as src_group,
                COUNT(*),
                ROUND(COUNT(*) * 100.0 / ?, 2)
            FROM places
            GROUP BY src_group
            ORDER BY COUNT(*) DESC
        """, (total_places,))
        for src, cnt, pct in cur.fetchall():
            lines.append(f"  * {src} : {cnt:,} ({pct}%)")
            
        # 5. Focus sur les 140 entrées OSM
        lines.append("\n--- Détail des 140 entrées OpenStreetMap fusionnées ---")
        cur.execute("""
            SELECT wilaya, categorie_recherche, COUNT(*)
            FROM places
            WHERE source LIKE 'osm_overpass%'
            GROUP BY wilaya, categorie_recherche
            ORDER BY wilaya, COUNT(*) DESC
        """)
        osm_by_cat = cur.fetchall()
        for w, cat, cnt in osm_by_cat:
            lines.append(f"  * {w} [{cat}] : {cnt}")
            
        # Coordonnées des entrées OSM
        cur.execute("""
            SELECT 
                MIN(latitude), MAX(latitude),
                MIN(longitude), MAX(longitude),
                COUNT(CASE WHEN telephone IS NOT NULL AND telephone != '' THEN 1 END),
                COUNT(CASE WHEN adresse IS NOT NULL AND adresse != '' THEN 1 END),
                COUNT(CASE WHEN commune IS NOT NULL AND commune != '' THEN 1 END)
            FROM places
            WHERE source LIKE 'osm_overpass%'
        """)
        min_lat, max_lat, min_lon, max_lon, osm_tel, osm_adr, osm_com = cur.fetchone()
        lines.append(f"  * Bornes GPS OSM : Lat [{min_lat:.4f} à {max_lat:.4f}], Lon [{min_lon:.4f} à {max_lon:.4f}]")
        lines.append(f"  * Téléphones renseignés : {osm_tel}/140 ({osm_tel*100.0/140:.1f}%)")
        lines.append(f"  * Adresses renseignées : {osm_adr}/140 ({osm_adr*100.0/140:.1f}%)")
        lines.append(f"  * Communes renseignées : {osm_com}/140 ({osm_com*100.0/140:.1f}%)")

        # 6. Complétude globale de la base
        lines.append("\n--- Complétude globale des champs (sur 23,669 entrées) ---")
        cur.execute("""
            SELECT
                COUNT(CASE WHEN nom IS NOT NULL AND TRIM(nom) != '' THEN 1 END) as nom_cnt,
                COUNT(CASE WHEN wilaya IS NOT NULL AND TRIM(wilaya) != '' THEN 1 END) as wil_cnt,
                COUNT(CASE WHEN commune IS NOT NULL AND TRIM(commune) != '' THEN 1 END) as com_cnt,
                COUNT(CASE WHEN telephone IS NOT NULL AND TRIM(telephone) != '' THEN 1 END) as tel_cnt,
                COUNT(CASE WHEN adresse IS NOT NULL AND TRIM(adresse) != '' THEN 1 END) as adr_cnt,
                COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as gps_cnt,
                COUNT(CASE WHEN site_web IS NOT NULL AND TRIM(site_web) != '' THEN 1 END) as web_cnt,
                COUNT(CASE WHEN horaires IS NOT NULL AND TRIM(horaires) != '' THEN 1 END) as hor_cnt
            FROM places
        """)
        n_nom, n_wil, n_com, n_tel, n_adr, n_gps, n_web, n_hor = cur.fetchone()
        lines.append(f"  * Nom : {n_nom:,}/{total_places:,} ({n_nom*100.0/total_places:.2f}%)")
        lines.append(f"  * Wilaya : {n_wil:,}/{total_places:,} ({n_wil*100.0/total_places:.2f}%)")
        lines.append(f"  * Commune : {n_com:,}/{total_places:,} ({n_com*100.0/total_places:.2f}%)")
        lines.append(f"  * Téléphone : {n_tel:,}/{total_places:,} ({n_tel*100.0/total_places:.2f}%)")
        lines.append(f"  * Coordonnées GPS : {n_gps:,}/{total_places:,} ({n_gps*100.0/total_places:.2f}%)")
        lines.append(f"  * Adresse : {n_adr:,}/{total_places:,} ({n_adr*100.0/total_places:.2f}%)")
        lines.append(f"  * Site web : {n_web:,}/{total_places:,} ({n_web*100.0/total_places:.2f}%)")
        lines.append(f"  * Horaires : {n_hor:,}/{total_places:,} ({n_hor*100.0/total_places:.2f}%)")
        
        # 7. Validation géographique globale
        lines.append("\n--- Contrôle de cohérence géographique ---")
        cur.execute("""
            SELECT COUNT(*) 
            FROM places 
            WHERE latitude < 18.0 OR latitude > 38.0 OR longitude < -9.0 OR longitude > 12.0
        """)
        out_of_bounds = cur.fetchone()[0]
        lines.append(f"  * Coordonnées hors limites Algérie (18°-38°N, -9°-12°E) : {out_of_bounds}")
        
        # 8. Répartition par wilaya (58 wilayas)
        lines.append("\n--- Couverture par Wilaya (Top 10 et Flop 5) ---")
        cur.execute("""
            SELECT wilaya, COUNT(*) 
            FROM places 
            GROUP BY wilaya 
            ORDER BY COUNT(*) DESC
        """)
        wil_counts = cur.fetchall()
        lines.append(f"  * Nombre de wilayas distinctes couvertes : {len(wil_counts)}")
        lines.append("  * Top 10 wilayas :")
        for w, c in wil_counts[:10]:
            lines.append(f"      - {w} : {c:,}")
        lines.append("  * 5 wilayas les moins représentées :")
        for w, c in wil_counts[-5:]:
            lines.append(f"      - {w} : {c:,}")
            
        # 9. Analyse des doublons stricts et potentiels
        lines.append("\n--- Analyse des doublons ---")
        cur.execute("SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL")
        distinct_pids = cur.fetchone()[0]
        lines.append(f"  * place_id distincts : {distinct_pids:,}")
        lines.append(f"  * place_id NULL : {total_places - distinct_pids:,}")
        
        # Doublons par téléphone (uniquement numéros valides >= 8 chiffres)
        cur.execute("""
            SELECT telephone_normalized, COUNT(*)
            FROM places
            WHERE telephone_normalized IS NOT NULL AND LENGTH(telephone_normalized) >= 8
            GROUP BY telephone_normalized
            HAVING COUNT(*) > 1
        """)
        phone_dups = cur.fetchall()
        lines.append(f"  * Numéros de téléphone partagés par plusieurs entrées : {len(phone_dups):,}")
        
    lines.append("\n" + "=" * 70)
    lines.append("FIN DU RAPPORT D'AUDIT PHASE 9.1")
    lines.append("=" * 70)
    
    report_text = "\n".join(lines)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report_text)
        
    # Print safe summary to stdout
    print(f"Audit Phase 9.1 terminé. Rapport écrit dans : {REPORT}")
    print(f"Total places : {total_places}")
    print(f"Intégrité : {integ}")
    print(f"SHA-256 : {sha_prod}")

if __name__ == "__main__":
    run_audit()
