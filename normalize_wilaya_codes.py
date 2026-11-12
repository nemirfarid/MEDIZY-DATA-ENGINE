import sqlite3

db = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = db.cursor()

# Normalize wilaya_code to 2-digit strings in facilities
c.execute("UPDATE facilities SET wilaya_code = printf('%02d', CAST(wilaya_code AS INTEGER))")
print(f"Updated facilities: {c.rowcount}")

# Normalize wilaya_code in communes
c.execute("UPDATE communes SET wilaya_code = printf('%02d', CAST(wilaya_code AS INTEGER))")
print(f"Updated communes: {c.rowcount}")

db.commit()

# Verify
c.execute("SELECT DISTINCT wilaya_code FROM facilities ORDER BY wilaya_code")
codes = [r[0] for r in c.fetchall()]
print(f"Facilities wilaya codes: {codes}")
print(f"Count: {len(codes)}")

c.execute("SELECT DISTINCT wilaya_code FROM communes ORDER BY wilaya_code")
ccodes = [r[0] for r in c.fetchall()]
print(f"Communes wilaya codes count: {len(ccodes)}")

db.close()