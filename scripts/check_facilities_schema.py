import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("PRAGMA table_info(facilities)")
print("facilities columns:", [col[1] for col in c.fetchall()])

