import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()
c.execute("SELECT count(1) FROM facilities WHERE commune IS NULL OR trim(commune) = '' OR commune = 'nan'")
print("Facilities with missing or invalid commune:", c.fetchone()[0])

# When commune is missing, set commune = wilaya (Chef-lieu) so commune button/chips always work!
c.execute("""
    UPDATE facilities 
    SET commune = wilaya 
    WHERE commune IS NULL OR trim(commune) = '' OR commune = 'nan'
""")
print(f"Updated {c.rowcount} facilities to default commune = wilaya")

conn.commit()
conn.close()

