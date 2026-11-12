import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Clean up temporary commune codes like '5', 'Rue du wilaya', 'P56G+88X', 'P5C9+Q47', 'رقان', 'تيطاف'
c.execute("""
    UPDATE facilities 
    SET commune = 'Reggane' 
    WHERE wilaya_code = '01' AND (commune IN ('5', 'Rue du wilaya', 'P56G+88X', 'P5C9+Q47', 'رقan', 'رقان') OR nom LIKE '%Reggane%')
""")

c.execute("""
    UPDATE facilities 
    SET commune = 'Tit' 
    WHERE wilaya_code = '01' AND (commune LIKE '%تيطاف%' OR nom LIKE '%تيطاف%')
""")

conn.commit()

print("Commune distribution in Wilaya 01 (Adrar):")
for r in c.execute("SELECT commune, count(1) FROM facilities WHERE wilaya_code = '01' GROUP BY commune ORDER BY count(1) DESC").fetchall():
    print("  *", r)

conn.close()

