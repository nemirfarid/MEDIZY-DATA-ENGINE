import sqlite3

conn = sqlite3.connect('medizy_scraper.db')
c = conn.cursor()

# Get total places per wilaya in medizy_scraper.db
c.execute("""
    SELECT wilaya, count(1) 
    FROM places 
    GROUP BY wilaya 
    ORDER BY count(1) DESC
""")
rows = c.fetchall()
print(f"Total wilayas represented in medizy_scraper.db: {len(rows)}")
for r in rows:
    print(f"  {r[0]} : {r[1]} places")

conn.close()

