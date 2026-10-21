import sqlite3
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Get schema for places table
c.execute('PRAGMA table_info(places)')
cols = c.fetchall()
print("Places columns:")
for col in cols:
    print(f"  {col[1]} ({col[2]})")

# Sample data
c.execute('SELECT * FROM places LIMIT 3')
rows = c.fetchall()
print("\nSample places:")
for row in rows:
    print(row)

# Check wilayas, communes, categories
c.execute('PRAGMA table_info(wilayas)')
print("\nWilayas columns:", c.fetchall())
c.execute('PRAGMA table_info(communes)')
print("Communes columns:", c.fetchall())
c.execute('PRAGMA table_info(categories)')
print("Categories columns:", c.fetchall())

# Check data_quality
c.execute('SELECT * FROM data_quality')
print("\nData quality:", c.fetchall())

conn.close()