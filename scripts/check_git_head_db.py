import subprocess
import sqlite3
import os

subprocess.run(["git", "show", "HEAD:assets/data/sante_dz_bundled.db"], stdout=open("temp_git_db.db", "wb"))
conn = sqlite3.connect("temp_git_db.db")
c = conn.cursor()
c.execute("SELECT count(*) FROM facilities")
print("Facilities count in git commit HEAD:", c.fetchone()[0])
c.execute("SELECT nom, commune, wilaya FROM facilities WHERE nom LIKE '%Ainouch%'")
print("Ainouch in HEAD:", c.fetchall())
conn.close()
os.remove("temp_git_db.db")

