#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Audit script for medizy_scraper.db production database.
Real, read-only analysis of actual data state.
"""
import sqlite3, hashlib, os
from datetime import datetime

PROD = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
REPORT = r"C:\SANTE_DZ_SCRAPER\phase8_3_corrected_report.txt"

def main():
    conn = sqlite3.connect(PROD)
    cur = conn.cursor()
    
    lines = []
    lines.append("PHASE 8.3 - CORRECTED AUDIT OF PRODUCTION (medizy_scraper.db)")
    lines.append("Date: " + datetime.now().isoformat())
    lines.append("")
    lines.append("1) PRODUCTION INFO")
    
    # Total count
    cur.execute("SELECT COUNT(*) FROM places")
    total = cur.fetchone()[0]
    lines.append("Total entries: " + str(total))
    
    # Integrity
    cur.execute("PRAGMA integrity_check")
    integrity = cur.fetchone()[0]
    lines.append("Integrity: " + integrity)
    
    # Columns
    cur.execute("PRAGMA table_info(places)")
    cols = cur.fetchall()
    lines.append("Number of columns: " + str(len(cols)))
    lines.append("Columns: " + ", ".join([c[1] for c in cols]))
    lines.append("")
    
    lines.append("2) WILAYA_ID / WILAYA ANALYSIS")
    cur.execute("SELECT COUNT(*) FROM places WHERE wilaya IS NULL OR wilaya = ''")
    wilaya_missing = cur.fetchone()[0]
    lines.append("Entries with missing wilaya: " + str(wilaya_missing))
    
    cur.execute("SELECT wilaya, COUNT(*) as cnt FROM places WHERE wilaya IS NOT NULL AND wilaya != '' GROUP BY wilaya ORDER BY cnt DESC LIMIT 5")
    top_wilayas = cur.fetchall()
    for w in top_wilayas:
        lines.append("  Wilaya '" + str(w[0]) + "': " + str(w[1]))
    lines.append("")
    
    lines.append("3) PLACE_ID DUPLICATE ANALYSIS")
    cur.execute("SELECT COUNT(*) FROM places")
    total_check = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL")
    distinct_place_ids = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM places WHERE place_id IS NULL OR place_id = ''")
    place_id_missing = cur.fetchone()[0]
    lines.append("Total entries: " + str(total_check))
    lines.append("Distinct place_id: " + str(distinct_place_ids))
    lines.append("Entries with missing/null place_id: " + str(place_id_missing))
    lines.append("Potential duplicates (total - distinct): " + str(total_check - distinct_place_ids))
    lines.append("")
    
    lines.append("4) DATA QUALITY (key fields)")
    cur.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ''")
    phone_count = cur.fetchone()[0]
    lines.append("Entries with telephone: " + str(phone_count))
    lines.append("Telephone coverage rate: " + str(round(phone_count/total * 100, 1)) + "%")
    
    cur.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    gps_count = cur.fetchone()[0]
    lines.append("Entries with GPS coordinates: " + str(gps_count))
    lines.append("GPS coverage rate: " + str(round(gps_count/total * 100, 1)) + "%")
    
    cur.execute("SELECT COUNT(*) FROM places WHERE site_web IS NOT NULL AND site_web != ''")
    website_count = cur.fetchone()[0]
    lines.append("Entries with website: " + str(website_count))
    lines.append("Website coverage rate: " + str(round(website_count/total * 100, 1)) + "%")
    lines.append("")
    
    lines.append("5) SOURCE ANALYSIS")
    cur.execute("SELECT source, COUNT(*) FROM places WHERE source IS NOT NULL GROUP BY source ORDER BY COUNT(*) DESC LIMIT 10")
    sources = cur.fetchall()
    for s in sources:
        lines.append("  Source '" + str(s[0]) + "': " + str(s[1]))
    lines.append("")
    
    lines.append("6) STATUS VALUES")
    cur.execute("SELECT status, COUNT(*) FROM places GROUP BY status")
    for s in cur.fetchall():
        lines.append("  Status '" + str(s[0]) + "': " + str(s[1]))
    lines.append("")
    
    conn.close()
    
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Report written:", REPORT)

if __name__ == "__main__":
    main()
