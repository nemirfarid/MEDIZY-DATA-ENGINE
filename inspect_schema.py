import sqlite3

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_test.db')
cursor = conn.cursor()

# Get schema for places table
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='places';")
print('PLACES TABLE SCHEMA:')
print(cursor.fetchone()[0])
print()

# Get schema for other tables
for table in ['wilayas', 'communes', 'categories', 'scrape_tasks', 'scrape_runs', 'dedup_candidates', 'data_quality']:
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
    result = cursor.fetchone()
    if result:
        print(f'{table.upper()} TABLE SCHEMA:')
        print(result[0])
        print()

# Check indexes
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='places';")
print('PLACES INDEXES:')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}')

# Check foreign keys
cursor.execute("PRAGMA foreign_key_list(places);")
print('\nPLACES FOREIGN KEYS:')
for row in cursor.fetchall():
    print(f'  {row}')

conn.close()