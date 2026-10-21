import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db')
cursor = conn.cursor()

# Check integrity
cursor.execute('PRAGMA integrity_check;')
print('Integrity:', cursor.fetchall())

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print('Tables:', cursor.fetchall())

# Count entries in main table
for table in ['etablissements', 'etablissement', 'health_facilities', 'facilities']:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table};')
        count = cursor.fetchone()
        print(f'{table} count:', count)
    except:
        pass

conn.close()