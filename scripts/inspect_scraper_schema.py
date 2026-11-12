import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()

# Check schema of communes and categories
c.execute("PRAGMA table_info(communes)")
print("Communes schema:", [r[1] for r in c.fetchall()])

c.execute("PRAGMA table_info(categories)")
print("Categories schema:", [r[1] for r in c.fetchall()])

c.execute("PRAGMA table_info(places)")
print("Places schema:", [r[1] for r in c.fetchall()])

print("\nCategories in medizy_scraper.db:")
for r in c.execute("SELECT * FROM categories").fetchall():
    print("  ", r)

print("\nCommunes of Wilaya 01 (Adrar) in medizy_scraper.db:")
for r in c.execute("SELECT * FROM communes WHERE wilaya_id = 1 OR wilaya_code = '01' OR wilaya_id = '01'").fetchall():
    print("  ", r)

conn.close()

