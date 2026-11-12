import sqlite3
import pandas as pd

# Check structures table vs facilities
conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check what sources exist in structures
c.execute("SELECT source_csv, count(*) FROM structures GROUP BY source_csv")
print("Structures by source_csv:")
for r in c.fetchall():
    print(r)

# Check is_verified count
c.execute("SELECT is_verified, count(*) FROM structures GROUP BY is_verified")
print("Structures by is_verified:")
for r in c.fetchall():
    print(r)

# Check differences between structures and facilities
# structures has 59637, facilities has 56078
print("Structures total:", c.execute("SELECT count(*) FROM structures").fetchone()[0])
print("Facilities total:", c.execute("SELECT count(*) FROM facilities").fetchone()[0])

conn.close()

