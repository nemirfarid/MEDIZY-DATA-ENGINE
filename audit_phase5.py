#!/usr/bin/env Python3
"""
Phase 5 — Étape 1: Audit en lecture seule de la base MEDIZY.
- Chemin exact de la base active
- Nombre d'entrées, 58 wilayas, clés uniques, doublons
- Coordoonnées GPS invalides ou hors d'Algérie
- Cohérence des noms, téléphones, adresses, URL, notes
- Confirmation que 935 CANDIDATE sont exclues
- Vérification des sauvegardes
"""
import sqlite3, json, sys, os
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'

# Alger coordinate bounds (rough)
ALGERIA_LAT_MIN, ALGERIA_LAT_MAX = 19.5, 37.5
ALGERIA_LNG_MIN, ALGERIA_LNG_MAX = -8.5, 12.0

def main():
    results = {}

    # 1. Exact DB path
    db_path = Path(DB_PATH)
    results['db_path'] = str(db_path)
    results['db_exists'] = db_path.exists()
    results['db_size_bytes'] = db_path.stat().st_size if db_path.exists() else 0

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 2. Entry count and schema
    cur.execute("SELECT COUNT(*) as cnt FROM places")
    results['total_entries'] = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(DISTINCT wilaya) as cnt FROM places")
    results['wilayas_count'] = cur.fetchone()['cnt']

    cur.execute("SELECT DISTINCT wilaya FROM places ORDER BY wilaya")
    results['wilayas'] = [r['wilaya'] for r in cur.fetchall()]

    # 3. Unique keys and duplicates
    cur.execute("SELECT COUNT(DISTINCT place_id) as cnt FROM places WHERE place_id IS NOT NULL AND place_id != ''")
    results['unique_place_ids'] = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(DISTINCT google_maps_url) as cnt FROM places WHERE google_maps_url IS NOT NULL")
    results['unique_urls'] = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(DISTINCT nom) as cnt FROM places WHERE nom IS NOT NULL AND nom != ''")
    results['unique_names'] = cur.fetchone()['cnt']

    # Duplicate detection by place_id
    cur.execute("""
        SELECT place_id, COUNT(*) as cnt FROM places 
        WHERE place_id IS NOT NULL AND place_id != ''
        GROUP BY place_id HAVING COUNT(*) > 1
    """)
    dup_place_ids = cur.fetchall()
    results['duplicate_place_ids'] = len(dup_place_ids)

    # Duplicate detection by URL
    cur.execute("""
        SELECT google_maps_url, COUNT(*) as cnt FROM places 
        WHERE google_maps_url IS NOT NULL AND google_maps_url != ''
        GROUP BY google_maps_url HAVING COUNT(*) > 1
    """)
    dup_urls = cur.fetchall()
    results['duplicate_urls'] = len(dup_urls)

    # 4. GPS validation
    cur.execute("SELECT COUNT(*) as cnt FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    results['entries_with_gps'] = cur.fetchone()['cnt']

    cur.execute("""
        SELECT COUNT(*) as cnt FROM places 
        WHERE latitude IS NOT NULL 
          AND longitude IS NOT NULL
          AND latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
    """, (ALGERIA_LAT_MIN, ALGERIA_LAT_MAX, ALGERIA_LNG_MIN, ALGERIA_LNG_MAX))
    results['gps_in_algeria'] = cur.fetchone()['cnt']

    cur.execute("""
        SELECT COUNT(*) as cnt FROM places 
        WHERE latitude IS NOT NULL 
          AND longitude IS NOT NULL
          AND (latitude < ? OR latitude > ? OR longitude < ? OR longitude > ?)
    """, (ALGERIA_LAT_MIN, ALGERIA_LAT_MAX, ALGERIA_LNG_MIN, ALGERIA_LNG_MAX))
    results['gps_outside_algeria'] = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM places WHERE latitude IS NULL AND longitude IS NULL")
    results['entries_no_gps'] = cur.fetchone()['cnt']

    # List entries with GPS outside Algeria
    cur.execute("""
        SELECT nom, wilaya, latitude, longitude, google_maps_url 
        FROM places 
        WHERE latitude IS NOT NULL 
          AND longitude IS NOT NULL
          AND (latitude < ? OR latitude > ? OR longitude < ? OR longitude > ?)
        LIMIT 20
    """, (ALGERIA_LAT_MIN, ALGERIA_LAT_MAX, ALGERIA_LNG_MIN, ALGERIA_LNG_MAX))
    results['gps_outside_algeria_samples'] = [dict(r) for r in cur.fetchall()]

    # 5. Data consistency checks
    # Empty/nom_inconnu names
    cur.execute("SELECT COUNT(*) as cnt FROM places WHERE nom IS NULL OR nom = '' OR nom = 'Inconnu'")
    results['invalid_names'] = cur.fetchone()['cnt']

    # Phone format validation (should start with 0 or +)
    cur.execute("""
        SELECT COUNT(*) as cnt FROM places 
        WHERE telephone IS NOT NULL AND telephone != ''
          AND telephone NOT GLOB '0[0-9]*'
          AND telephone NOT GLOB '+213[0-9]*'
    """)
    results['invalid_phone_format'] = cur.fetchone()['cnt']

    # Empty address
    cur.execute("SELECT COUNT(*) as cnt FROM places WHERE adresse IS NULL OR adresse = ''")
    results['empty_addresses'] = cur.fetchone()['cnt']

    # Invalid URL
    cur.execute("""
        SELECT COUNT(*) as cnt FROM places 
        WHERE google_maps_url IS NULL 
          OR google_maps_url = '' 
          OR (google_maps_url NOT LIKE 'http%' AND google_maps_url NOT LIKE 'https%')
    """)
    results['invalid_urls'] = cur.fetchone()['cnt']

    # Invalid rating (not a number between 1-5)
    cur.execute("""
        SELECT COUNT(*) as cnt FROM places 
        WHERE note IS NOT NULL AND note != ''
          AND (note NOT GLOB '[0-9].*' OR CAST(note AS REAL) < 0 OR CAST(note AS REAL) > 5)
    """)
    results['invalid_ratings'] = cur.fetchone()['cnt']

    # 6. Confirm CANDIDATE exclusion
    cur.execute("SELECT name_status, COUNT(*) as cnt FROM places GROUP BY name_status")
    results['name_status_distribution'] = dict(cur.fetchall())

    cur.execute("SELECT COUNT(*) as cnt FROM places WHERE name_status = 'CANDIDATE'")
    results['candidate_in_db'] = cur.fetchone()['cnt']

    # Check checkpoint for CANDIDATE count
    with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
        import csv
        reader = csv.DictReader(f)
        ckpt_rows = list(reader)
    ckpt_candidates = sum(1 for r in ckpt_rows if r.get('name_status', 'VERIFIED') == 'CANDIDATE')
    results['candidate_in_checkpoint'] = ckpt_candidates

    # 7. Backup verification
    backups = [
        r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_import.db',
        r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_enrich_import.db',
        r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_field_enrich.db',
    ]
    backup_status = []
    for b in backups:
        exists = os.path.exists(b)
        readable = False
        entry_count = None
        if exists:
            try:
                bconn = sqlite3.connect(b)
                bcur = bconn.cursor()
                bcur.execute("SELECT COUNT(*) FROM places")
                entry_count = bcur.fetchone()[0]
                readable = True
                bconn.close()
            except Exception as e:
                readable = False
                entry_count = str(e)
        backup_status.append({
            'path': b,
            'exists': exists,
            'readable': readable,
            'entries': entry_count,
        })
    results['backups'] = backup_status

    conn.close()

    # Write JSON report
    report_json = Path(r'D:\SANTE_DZ_EXPORTS\audit_phase5.json')
    with open(report_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"Rapport JSON écrit: {report_json}")

    # Write Markdown report
    report_md = Path(r'D:\SANTE_DZ_EXPORTS\audit_phase5.md')
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# Phase 5 — Étape 1: Audit Lecture Seule\n\n")
        f.write(f"**Date**: {datetime.now().isoformat()}\n\n")
        f.write(f"**Base active**: `{results['db_path']}`\n\n")
        f.write(f"**Exists**: {results['db_exists']}\n")
        f.write(f"**Taille**: {results['db_size_bytes']:,} octets\n\n")

        f.write("## 1. Entrées et Wilayas\n\n")
        f.write(f"- Total entrées: **{results['total_entries']}**\n")
        f.write(f"- Wilayas distinctes: **{results['wilayas_count']}**\n")
        f.write(f"- Wilayas: {', '.join(results['wilayas'])}\n\n")

        f.write("## 2. Clés Unies et Doublons\n\n")
        f.write(f"- Unique place_ids: {results['unique_place_ids']}\n")
        f.write(f"- Unique URLs: {results['unique_urls']}\n")
        f.write(f"- Noms uniques: {results['unique_names']}\n")
        f.write(f"- Doublons par place_id: **{results['duplicate_place_ids']}**\n")
        f.write(f"- Doublons par URL: **{results['duplicate_urls']}**\n\n")

        f.write("## 3. Validation GPS\n\n")
        f.write(f"- Entrées avec GPS: {results['entries_with_gps']}\n")
        f.write(f"- GPS dans les limites Algérie: {results['gps_in_algeria']}\n")
        f.write(f"- GPS hors Algérie: **{results['gps_outside_algeria']}**\n")
        f.write(f"- Entrées sans GPS: {results['entries_no_gps']}\n\n")

        if results['gps_outside_algeria_samples']:
            f.write("### Échantillons GPS hors Algérie\n\n")
            for s in results['gps_outside_algeria_samples']:
                f.write(f"- {s['nom'][:50]} ({s['wilaya']}) GPS: {s['latitude']}, {s['longitude']}\n")
            f.write("\n")

        f.write("## 4. Cohérence des Données\n\n")
        f.write(f"- Noms invalides/empty: {results['invalid_names']}\n")
        f.write(f"- Téléphones format invalide: {results['invalid_phone_format']}\n")
        f.write(f"- Adresses vides: {results['empty_addresses']}\n")
        f.write(f"- URLs invalides: {results['invalid_urls']}\n")
        f.write(f"- Notes invalides: {results['invalid_ratings']}\n\n")

        f.write("## 5. Confirmation Exclusion CANDIDATE\n\n")
        f.write(f"- CANDIDATE dans checkpoint: {results['candidate_in_checkpoint']}\n")
        f.write(f"- CANDIDATE dans DB: {results['candidate_in_db']}\n")
        f.write(f"- Répartition name_status: {results['name_status_distribution']}\n\n")

        f.write("## 6. Sauvegardes\n\n")
        for b in results['backups']:
            f.write(f"- `{b['path']}`\n")
            f.write(f"  - Exists: {b['exists']}, Readable: {b['readable']}, Entries: {b['entries']}\n")

        f.write("\n## Conclusion\n\n")
        f.write("Audit terminé en lecture seule. ")
        if results['duplicate_urls'] > 0:
            f.write(f"**{results['duplicate_urls']} doublons détectés par URL** — nécessitent un audit de déduplication. ")
        if results['gps_outside_algeria'] > 0:
            f.write(f"**{results['gps_outside_algeria']} entrées avec GPS hors Algérie** — nécessitent vérification. ")
        f.write("Voir rapport JSON pour les données complètes.\n")

    print(f"Rapport Markdown écrit: {report_md}")

    # Print summary to console
    print(f"\n=== RÉSUMÉ DE L'AUDIT ===")
    print(f"Total DB: {results['total_entries']}")
    print(f"Wilayas: {results['wilayas_count']}")
    print(f"Doublons URL: {results['duplicate_urls']}")
    print(f"Doublons place_id: {results['duplicate_place_ids']}")
    print(f"GPS hors Algérie: {results['gps_outside_algeria']}")
    print(f"Entrées sans GPS: {results['entries_no_gps']}")
    print(f"Noms invalides: {results['invalid_names']}")
    print(f"Téléphones invalides: {results['invalid_phone_format']}")
    print(f"Adresses vides: {results['empty_addresses']}")
    print(f"URLs invalides: {results['invalid_urls']}")
    print(f"Notes invalides: {results['invalid_ratings']}")
    print(f"CANDIDATE dans DB: {results['candidate_in_db']}")
    print(f"CANDIDATE dans checkpoint: {results['candidate_in_checkpoint']}")
    print(f"Backups vérifiés: {sum(1 for b in results['backups'] if b['readable'])}/{len(results['backups'])}")

if __name__ == '__main__':
    main()
