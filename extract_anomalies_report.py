import os
import sys
import csv
import json
import hashlib
import sqlite3
from pathlib import Path

PROD_DB = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
BASELINE_DB = r"D:\SANTE_DZ_EXPORTS\backups\medizy_scraper_phase1_baseline.db"
SANDBOX_DB = r"D:\SANTE_DZ_EXPORTS\medizy_scraper_sandbox.db"
REPORTS_DIR = r"D:\SANTE_DZ_EXPORTS\reports"

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def verify_db(filepath):
    sha = compute_sha256(filepath)
    size = os.path.getsize(filepath)
    uri = f"file:{Path(filepath).as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    c = conn.cursor()
    c.execute("PRAGMA integrity_check;")
    integrity = c.fetchone()[0]
    conn.close()
    return {"path": filepath, "size": size, "sha256": sha, "integrity": integrity}

def export_to_csv(filepath, fieldnames, rows):
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def export_to_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_anomalies():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # 1. Verification of all three DBs
    verifications = {
        "production": verify_db(PROD_DB),
        "baseline_backup": verify_db(BASELINE_DB),
        "sandbox": verify_db(SANDBOX_DB)
    }
    
    # Check strict equality of SHA256
    expected_sha = "948fda84d6375b6b1dbd7ba822cdcfe09f7301f81f8779bc803e717b582c493d"
    for name, v in verifications.items():
        v["matches_expected_sha"] = (v["sha256"] == expected_sha)

    # 2. Extract anomalies from SANDBOX in read-only
    sandbox_uri = f"file:{Path(SANDBOX_DB).as_posix()}?mode=ro"
    conn = sqlite3.connect(sandbox_uri, uri=True)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Columns
    c.execute("PRAGMA table_info(places);")
    fieldnames = [col["name"] for col in c.fetchall()]
    
    # Total places
    c.execute("SELECT COUNT(*) FROM places;")
    total_records = c.fetchone()[0]
    
    # Anomaly a: Google Fonts artifact (phone 0104346352 or site fonts.gstatic.com)
    c.execute("""
        SELECT * FROM places 
        WHERE telephone = '0104346352' 
           OR telephone_raw = '0104346352' 
           OR site_web LIKE '%fonts.gstatic.com%'
        ORDER BY id;
    """)
    rows_fonts = [dict(r) for r in c.fetchall()]
    
    # Anomaly b: National centroid GPS (lat 28.09487, lon 1.66544)
    c.execute("""
        SELECT * FROM places 
        WHERE ROUND(latitude, 5) = 28.09487 AND ROUND(longitude, 5) = 1.66544
        ORDER BY id;
    """)
    rows_centroid = [dict(r) for r in c.fetchall()]
    
    # Anomaly c: External links (sante-dz.com / tibdz)
    c.execute("""
        SELECT * FROM places 
        WHERE site_web LIKE '%sante-dz.com%' OR site_web LIKE '%tibdz%'
        ORDER BY id;
    """)
    rows_external = [dict(r) for r in c.fetchall()]
    
    conn.close()
    
    # Save files to D:\SANTE_DZ_EXPORTS\reports
    fonts_csv = os.path.join(REPORTS_DIR, "anomalies_google_fonts.csv")
    fonts_json = os.path.join(REPORTS_DIR, "anomalies_google_fonts.json")
    export_to_csv(fonts_csv, fieldnames, rows_fonts)
    export_to_json(fonts_json, rows_fonts)
    
    centroid_csv = os.path.join(REPORTS_DIR, "anomalies_centroid_gps.csv")
    centroid_json = os.path.join(REPORTS_DIR, "anomalies_centroid_gps.json")
    export_to_csv(centroid_csv, fieldnames, rows_centroid)
    export_to_json(centroid_json, rows_centroid)
    
    external_csv = os.path.join(REPORTS_DIR, "anomalies_external_urls.csv")
    external_json = os.path.join(REPORTS_DIR, "anomalies_external_urls.json")
    export_to_csv(external_csv, fieldnames, rows_external)
    export_to_json(external_json, rows_external)
    
    # Check overlaps between anomalies
    ids_fonts = set(r["id"] for r in rows_fonts)
    ids_centroid = set(r["id"] for r in rows_centroid)
    ids_external = set(r["id"] for r in rows_external)
    
    all_anomalous_ids = ids_fonts | ids_centroid | ids_external
    total_anomalous = len(all_anomalous_ids)
    clean_records_count = total_records - total_anomalous
    
    overlap_fonts_centroid = len(ids_fonts & ids_centroid)
    overlap_fonts_external = len(ids_fonts & ids_external)
    overlap_centroid_external = len(ids_centroid & ids_external)
    
    # Centroid breakdown by real wilaya
    centroid_by_wilaya = {}
    for r in rows_centroid:
        w = r["wilaya"] or "NON DEFINIE"
        centroid_by_wilaya[w] = centroid_by_wilaya.get(w, 0) + 1

    summary = {
        "verifications": verifications,
        "metrics": {
            "total_records": total_records,
            "google_fonts_artifact_count": len(rows_fonts),
            "centroid_gps_count": len(rows_centroid),
            "external_urls_count": len(rows_external),
            "overlaps": {
                "fonts_and_centroid": overlap_fonts_centroid,
                "fonts_and_external": overlap_fonts_external,
                "centroid_and_external": overlap_centroid_external
            },
            "distinct_anomalous_records": total_anomalous,
            "clean_records_count": clean_records_count,
            "sanitized_accuracy_rate": round(clean_records_count / total_records * 100, 4)
        },
        "centroid_by_wilaya": dict(sorted(centroid_by_wilaya.items(), key=lambda x: x[1], reverse=True)),
        "report_files": {
            "google_fonts_csv": fonts_csv,
            "google_fonts_json": fonts_json,
            "centroid_gps_csv": centroid_csv,
            "centroid_gps_json": centroid_json,
            "external_urls_csv": external_csv,
            "external_urls_json": external_json
        }
    }
    
    summary_path = os.path.join(REPORTS_DIR, "anomalies_summary_report.json")
    export_to_json(summary_path, summary)
    
    return summary

if __name__ == "__main__":
    result = extract_anomalies()
    print("EXTRACTION COMPLETED SUCCESSFULLY.")
    print(json.dumps(result, indent=2))
