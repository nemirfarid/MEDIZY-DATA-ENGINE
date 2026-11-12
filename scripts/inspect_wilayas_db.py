import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()
rows = cur.execute("SELECT DISTINCT wilaya_code, wilaya FROM facilities WHERE wilaya LIKE '%mostaganem%'").fetchall()
print("Distinct wilaya values for Mostaganem in facilities:")
for r in rows:
    print(r)

# Check all distinct wilaya_code across facilities
wcodes = cur.execute("SELECT wilaya_code, count(*) FROM facilities GROUP BY wilaya_code ORDER BY wilaya_code").fetchall()
print(f"Total distinct wilaya_codes: {len(wcodes)}")
print("First 15 wilaya codes:")
for w in wcodes[:15]:
    print(w)

