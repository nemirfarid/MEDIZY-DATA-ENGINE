#!/usr/bin/env Python3
"""Verify DB state after import cleanup."""
import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Check error artifacts in DB
c.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%' OR nom LIKE '%timeout%' OR nom LIKE '%capt%' OR nom LIKE '%introuvable%'")
print(f"Artéfacts d'erreur dans DB: {c.fetchone()[0]}")

# Check commune distribution
c.execute("SELECT commune, COUNT(*) FROM places WHERE commune IS NOT NULL AND commune != '' GROUP BY commune ORDER BY COUNT(*) DESC LIMIT 10")
print(f"Top 10 communes: {c.fetchall()}")

# Check entries with empty commune
c.execute("SELECT COUNT(*) FROM places WHERE commune IS NULL OR commune = ''")
print(f"Entrées sans commune: {c.fetchone()[0]}")

# Check name_status distribution
c.execute("SELECT name_status, COUNT(*) FROM places GROUP BY name_status")
print(f"name_status distribution: {c.fetchall()}")

# Check recovered entries
c.execute("SELECT COUNT(*) FROM places WHERE name_status = 'RECOVERED'")
print(f"Entrées RECOVERED: {c.fetchone()[0]}")

# Total
c.execute("SELECT COUNT(*) FROM places")
print(f"Total DB: {c.fetchone()[0]}")

# Wilaya count
c.execute("SELECT COUNT(DISTINCT wilaya) FROM places")
print(f"Wilayas distinctes: {c.fetchone()[0]}")

# GPS
c.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL")
print(f"Entrées avec GPS: {c.fetchone()[0]}")

# Phone count
c.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ''")
print(f"Entrées avec téléphone: {c.fetchone()[0]}")

# Check what column name commune uses in CSV
import csv
with open(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv', 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    first = next(reader)
    print(f"\nCSV columns: {reader.fieldnames}")
    print(f"commune value in first row: '{first.get('commune', 'NOT FOUND')}'")

conn.close()
