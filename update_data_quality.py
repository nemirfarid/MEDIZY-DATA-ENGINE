#!/usr/bin/env Python3
"""Update data_quality table with final metrics."""
import sqlite3, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Compute fresh metrics
c.execute("SELECT COUNT(*) FROM places")
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL")
gps = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ''")
phone = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE adresse IS NOT NULL AND adresse != ''")
adr = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE site_web IS NOT NULL AND site_web != ''")
web = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT categorie_recherche) FROM places")
cats = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE place_id IS NOT NULL AND place_id != ''")
pid = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE note IS NOT NULL AND note != ''")
rating = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE horaires IS NOT NULL AND horaires != ''")
hours = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT wilaya) FROM places")
wilayas = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT google_maps_url) FROM places")
urls = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%' OR nom LIKE '%timeout%'")
artifacts = c.fetchone()[0]

c.execute('''
    INSERT INTO data_quality (measured_at, total_places, gps_count, phone_count, address_count,
                              website_count, category_count, place_id_count, rating_count,
                              opening_hours_count, commune_count, duplicate_estimate, wilaya_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (datetime.now().isoformat(), total, gps, phone, adr, web, cats, pid, rating, hours, 0, 0, wilayas))
conn.commit()

print(f'Updated data_quality:')
print(f'  total_places: {total}')
print(f'  gps_count: {gps}')
print(f'  phone_count: {phone}')
print(f'  address_count: {adr}')
print(f'  website_count: {web}')
print(f'  category_count: {cats}')
print(f'  place_id_count: {pid}')
print(f'  rating_count: {rating}')
print(f'  opening_hours_count: {hours}')
print(f'  wilaya_count: {wilayas}')
print(f'  error_artifacts: {artifacts}')
print(f'  unique_urls: {urls}')
conn.close()
