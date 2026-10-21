import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Scrape runs
c.execute("SELECT * FROM scrape_runs")
rows = c.fetchall()
print(f'scrape_runs: {len(rows)}')
for r in rows:
    print(r)

# Scrape tasks
c.execute("SELECT * FROM scrape_tasks")
rows = c.fetchall()
print(f'scrape_tasks: {len(rows)}')
for r in rows[:10]:
    print(r)

# Source distribution in places
c.execute("SELECT source, COUNT(*) FROM places GROUP BY source")
print('\nPlaces by source:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')

# Categories distribution
c.execute("SELECT categorie_recherche, COUNT(*) FROM places GROUP BY categorie_recherche ORDER BY COUNT(*) DESC")
print('\nPlaces by category:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')

# Wilaya distribution
c.execute("SELECT wilaya, COUNT(*) FROM places GROUP BY wilaya ORDER BY COUNT(*) DESC")
print('\nPlaces by wilaya:')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]}')

conn.close()
