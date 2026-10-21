import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
cursor = conn.cursor()

# Check Biskra categories
cursor.execute('''SELECT categorie_recherche, COUNT(*) as cnt FROM places 
WHERE wilaya = "Biskra" GROUP BY categorie_recherche ORDER BY cnt DESC''')
rows = cursor.fetchall()
print(f"Biskra categories ({len(rows)}):")
for r in rows:
    print(f"  {r[0]}: {r[1]}")

# Total Biskra entries
cursor.execute('SELECT COUNT(*) FROM places WHERE wilaya = "Biskra"')
print(f"\nTotal Biskra entries: {cursor.fetchone()[0]}")

# Check how many categories should exist
cursor.execute('SELECT DISTINCT categorie_recherche FROM places ORDER BY categorie_recherche')
all_cats = [r[0] for r in cursor.fetchall()]
print(f"\nAll categories in DB ({len(all_cats)}):")
for c in all_cats:
    print(f"  {c}")

conn.close()