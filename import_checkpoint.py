#!/usr/bin/env python3
"""Import checkpoint.csv into medizy_scraper.db using sqlite_prototype mapping."""
import sqlite3, csv, os, sys, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, r'C:\SANTE_DZ_SCRAPER')
from sqlite_prototype import get_connection, import_checkpoint_to_sqlite

db_path = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
checkpoint_path = Path(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv')
backup_path = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_pre_import.db'

# Remove old backup if exists
if os.path.exists(backup_path):
    os.remove(backup_path)

# Backup AVANT import (using sqlite3 backup API)
print('Création du backup...')
conn = sqlite3.connect(db_path)
backup_conn = sqlite3.connect(backup_path)
conn.backup(backup_conn)
backup_conn.close()
conn.close()
print(f'Backup créé: {backup_path}')

# Connexion pour import
conn = get_connection(Path(db_path))
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM places')
before_count = cursor.fetchone()[0]
print(f'places avant import: {before_count}')

# Add new columns if they don't exist (for existing DBs created before these were added)
for col, ddl in [
    ('name_status', 'TEXT DEFAULT \'VERIFIED\''),
    ('name_source', 'TEXT'),
    ('recovery_date', 'TEXT'),
]:
    try:
        cursor.execute(f'ALTER TABLE places ADD COLUMN {col} {ddl}')
    except sqlite3.OperationalError:
        pass  # Column already exists

cursor.execute('DELETE FROM places')
conn.commit()
print('Table places vidée')

conn.close()

# Import using sqlite_prototype's function
import_checkpoint_to_sqlite(checkpoint_path, Path(db_path))

# Re-open for verifications
conn = get_connection(Path(db_path))
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM places')
after_count = cursor.fetchone()[0]
print(f'places après import: {after_count}')

cursor.execute('SELECT COUNT(DISTINCT wilaya) FROM places')
wilaya_count = cursor.fetchone()[0]
print(f'Distinct wilayas: {wilaya_count}')

cursor.execute('SELECT COUNT(DISTINCT nom) FROM places')
unique_names = cursor.fetchone()[0]
print(f'Noms uniques: {unique_names}')

cursor.execute('SELECT COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) FROM places')
gps_count = cursor.fetchone()[0]
print(f'Entrées avec GPS: {gps_count}')

cursor.execute('SELECT COUNT(DISTINCT categorie_recherche) FROM places')
unique_cats = cursor.fetchone()[0]
print(f'Catégories distinctes: {unique_cats}')

# Phone count
cursor.execute('SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ""')
phone_count = cursor.fetchone()[0]
print(f'Entrées avec téléphone: {phone_count}')

cursor.execute('SELECT COUNT(DISTINCT commune) FROM places')
commune_count = cursor.fetchone()[0]
print(f'Communnes distinctes: {commune_count}')

cursor.execute('SELECT COUNT(DISTINCT place_id) FROM places')
place_id_count = cursor.fetchone()[0]
print(f'place_id distincts: {place_id_count}')

cursor.execute('SELECT COUNT(DISTINCT google_maps_url) FROM places')
gm_url_count = cursor.fetchone()[0]
print(f'google_maps_url distinctes: {gm_url_count}')

# data_quality
cursor.execute('SELECT COUNT(*) FROM places')
total = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM places WHERE note IS NOT NULL AND note != ""')
rating_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM places WHERE horaires IS NOT NULL AND horaires != ""')
opening_hours_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM places WHERE adresse IS NOT NULL AND adresse != ""')
address_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM places WHERE site_web IS NOT NULL AND site_web != ""')
website_count = cursor.fetchone()[0]

cursor.execute("""
    INSERT INTO data_quality (measured_at, total_places, gps_count, phone_count, address_count,
                              website_count, category_count, place_id_count, rating_count,
                              opening_hours_count, commune_count, duplicate_estimate, wilaya_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (datetime.now().isoformat(), total, gps_count, phone_count, address_count,
      website_count, unique_cats, place_id_count, rating_count,
      opening_hours_count, commune_count, 0, wilaya_count))
conn.commit()
print('data_quality enregistré')

conn.close()
print('Import terminé avec succès')
