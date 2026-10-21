#!/usr/bin/env Python3
"""Final verification of DB and progression state."""
import json, sqlite3

# Check progression.json
with open(r'D:\SANTE_DZ_EXPORTS\scraping_progress.json', 'r', encoding='utf-8-sig') as f:
    prog = json.load(f)

print('=== scraping_progress.json ===')
print(f'Total national unique: {prog["total_national_unique"]}')
print(f'Status: {prog["status"]}')
print(f'Wilayas terminées: {len(prog["wilayas_terminees"])}')

if 'cleanup_phase3' in prog:
    c = prog['cleanup_phase3']
    print(f'DB entries after: {c["db_entries_after"]}')
    print(f'DB error artifacts after: {c["db_error_artifacts_after"]}')
    print(f'GPS coverage: {c["gps_coverage_pct"]}%')

# Verify DB
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM places")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM places WHERE nom LIKE '%impossible%' OR nom LIKE '%erreur%' OR nom LIKE '%timeout%'")
artifacts = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL")
gps = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != ''")
phones = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT wilaya) FROM places")
wilayas = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT categorie_recherche) FROM places")
cats = cur.fetchone()[0]

cur.execute("SELECT name_status, COUNT(*) FROM places GROUP BY name_status")
status = cur.fetchall()

conn.close()

print(f'\n=== DB Final State ===')
print(f'Total: {total}')
print(f'Artifacts: {artifacts}')
print(f'GPS: {gps} ({gps/total*100:.2f}%)')
print(f'Telephone: {phones} ({phones/total*100:.2f}%)')
print(f'Wilayas: {wilayas}')
print(f'Categories: {cats}')
print(f'Name status: {dict(status)}')

# Files modified
print(f'\n=== Fichiers modifiés ===')
modified_files = [
    'C:\\SANTE_DZ_SCRAPER\\sqlite_prototype.py',
    'C:\\SANTE_DZ_SCRAPER\\import_checkpoint.py',
    'C:\\SANTE_DZ_SCRAPER\\check_artifacts.py',
    'C:\\SANTE_DZ_SCRAPER\\phase3_cleanup.py',
    'C:\\SANTE_DZ_SCRAPER\\recover_names.py',
    'C:\\SANTE_DZ_SCRAPER\\verify_db.py',
    'D:\\SANTE_DZ_EXPORTS\\checkpoint.csv',
    'D:\\SANTE_DZ_EXPORTS\\scraping_progress.json',
]
for f in modified_files:
    print(f'  - {f}')
