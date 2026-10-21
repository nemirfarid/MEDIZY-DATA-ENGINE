import sqlite3
from collections import defaultdict

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Coverage by wilaya and category
cursor.execute("""
    SELECT wilaya, COUNT(*) as cnt
    FROM places
    WHERE wilaya IS NOT NULL
    GROUP BY wilaya
    ORDER BY COUNT(*) DESC
""")
wilaya_counts = {r['wilaya']: r['cnt'] for r in cursor.fetchall()}

cursor.execute("""
    SELECT categorie_recherche, COUNT(*) as cnt
    FROM places
    WHERE categorie_recherche IS NOT NULL
    GROUP BY categorie_recherche
    ORDER BY COUNT(*) DESC
""")
category_counts = {r['categorie_recherche']: r['cnt'] for r in cursor.fetchall()}

cursor.execute("SELECT COUNT(*) FROM places")
total = cursor.fetchone()[0]

print(f"Total DB entries: {total}")
print(f"Distinct wilayas: {len(wilaya_counts)}")
print(f"Distinct categories: {len(category_counts)}")
print("\nWilaya coverage:")
for w, c in sorted(wilaya_counts.items(), key=lambda x: -x[1]):
    print(f"  {w}: {c}")

print("\nCategory coverage:")
for cat, c in sorted(category_counts.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {c}")

# Check for GPS coverage
cursor.execute("""
    SELECT 
        wilaya,
        COUNT(*) as total,
        SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) as with_gps,
        SUM(CASE WHEN telephone IS NOT NULL AND telephone != '' THEN 1 ELSE 0 END) as with_phone,
        SUM(CASE WHEN adresse IS NOT NULL AND adresse != '' THEN 1 ELSE 0 END) as with_addr,
        SUM(CASE WHEN site_web IS NOT NULL AND site_web != '' THEN 1 ELSE 0 END) as with_site
    FROM places
    WHERE wilaya IS NOT NULL
    GROUP BY wilaya
    ORDER BY COUNT(*) DESC
""")
print("\nWilaya field coverage:")
print(f"{'Wilaya':<30} {'Total':>6} {'GPS':>6} {'Phone':>6} {'Addr':>6} {'Site':>6}")
for r in cursor.fetchall():
    print(f"{r['wilaya']:<30} {r['total']:>6} {r['with_gps']:>6} {r['with_phone']:>6} {r['with_addr']:>6} {r['with_site']:>6}")

conn.close()
