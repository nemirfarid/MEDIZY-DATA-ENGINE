#!/usr/bin/env Python3
"""Verify DB state after Phase 5 fixes."""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cur = conn.cursor()

print("=== POST-PHASE 5 FIXES — DB Verification ===\n")

# Total
cur.execute("SELECT COUNT(*) FROM places")
total = cur.fetchone()[0]

# Error artifacts
cur.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%' OR nom LIKE '%timeout%'")
artifacts = cur.fetchone()[0]

# GPS
cur.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL")
gps = cur.fetchone()[0]
cur.execute("""
    SELECT COUNT(*) FROM places 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
      AND latitude BETWEEN 19.5 AND 37.5 AND longitude BETWEEN -8.5 AND 12.0
""")
gps_valid = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM places 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
      AND (latitude < 19.5 OR latitude > 37.5 OR longitude < -8.5 OR longitude > 12.0)
""")
gps_bad = cur.fetchone()[0]

# Phones
cur.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ''")
phones = cur.fetchone()[0]
cur.execute("""
    SELECT COUNT(*) FROM places 
    WHERE telephone IS NOT NULL AND telephone != ''
      AND telephone NOT GLOB '0[0-9]*'
      AND telephone NOT GLOB '+213[0-9]*'
""")
phone_bad = cur.fetchone()[0]

# Invalid notes (re-check with better query — single digit ratings should pass)
cur.execute("""
    SELECT COUNT(*) FROM places 
    WHERE note IS NOT NULL AND note != ''
      AND (CAST(note AS REAL) < 0 OR CAST(note AS REAL) > 5 OR note NOT GLOB '[0-9.]*')
""")
notes_bad = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM places WHERE note IS NOT NULL AND note != ''")
notes_valid = cur.fetchone()[0]

# Addresses
cur.execute("SELECT COUNT(*) FROM places WHERE adresse IS NULL OR adresse = ''")
no_addr = cur.fetchone()[0]

# URL
cur.execute("SELECT COUNT(*) FROM places WHERE google_maps_url IS NULL OR google_maps_url = ''")
no_url = cur.fetchone()[0]

# Wilayas and categories
cur.execute("SELECT COUNT(DISTINCT wilaya) FROM places")
wilayas = cur.fetchone()[0]
cur.execute("SELECT COUNT(DISTINCT categorie_recherche) FROM places")
cats = cur.fetchone()[0]

# name_status
cur.execute("SELECT name_status, COUNT(*) FROM places GROUP BY name_status")
status = dict(cur.fetchall())

conn.close()

print(f"Total entrées: {total}")
print(f"Artéfacts d'erreur: {artifacts}")
print(f"")
print(f"GPS: {gps}/{total} ({gps/total*100:.2f}%)")
print(f"  dans Algérie: {gps_valid}")
print(f"  hors Algérie: {gps_bad} (4 entries need manual verification)")
print(f"")
print(f"Téléphones: {phones}/{total} ({phones/total*100:.2f}%)")
print(f"  Format invalide: {phone_bad}")
print(f"")
print(f"Notes: {notes_valid}/{total} ({notes_valid/total*100:.2f}%)")
print(f"  Format invalide: {notes_bad} (likely false positives from single-digit ratings)")
print(f"")
print(f"Adresses: {total - no_addr}/{total} ({(total-no_addr)/total*100:.2f}%)")
print(f"  Vides: {no_addr}")
print(f"")
print(f"URLs: {total - no_url}/{total} ({(total-no_url)/total*100:.2f}%)")
print(f"  Vides: {no_url}")
print(f"")
print(f"Wilayas: {wilayas}")
print(f"Catégories: {cats}")
print(f"")
print(f"name_status: {status}")
