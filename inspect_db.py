import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()

# Get schema
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
for row in cursor.fetchall():
    print(row[0])
    print()

# Get row counts
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for (table,) in tables:
    cursor.execute(f'SELECT COUNT(*) FROM [{table}]')
    print(f'{table}: {cursor.fetchone()[0]} rows')

# Sample data from main tables
for table_name in ['health_establishments', 'checkpoint_imports', 'wilaya_lookup', 'commune_lookup', 'notes_lookup', 'categories']:
    try:
        cursor.execute(f'SELECT * FROM [{table_name}] LIMIT 3')
        cols = [d[0] for d in cursor.description]
        print(f'\n{table_name} columns: {cols}')
        for row in cursor.fetchall():
            print(row)
    except:
        pass

conn.close()
