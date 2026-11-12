import sqlite3

conn_app = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn_app.cursor()
c.execute("SELECT DISTINCT wilaya, wilaya_code FROM facilities WHERE wilaya_code IS NOT NULL")
for r in c.fetchall():
    print(r)
conn_app.close()

