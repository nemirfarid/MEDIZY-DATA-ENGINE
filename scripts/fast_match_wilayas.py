import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Créer un index temporaire sur structures(nom_etablissement_praticien) pour que la jointure soit instantanée
c.execute("CREATE INDEX IF NOT EXISTS idx_struct_nom ON structures(nom_etablissement_praticien);")
conn.commit()

# Exécuter la mise à jour par batch via un curseur Python
c.execute("""
    SELECT s.nom_etablissement_praticien, s.code_wilaya, s.nom_wilaya, s.nom_commune
    FROM structures s
    WHERE s.source_csv = 'Google Maps Extractor 2026'
""")
rows = c.fetchall()
print(f"Chargé {len(rows)} structures réelles Google Maps...")

updates = []
for nom, code_w, nom_w, nom_c in rows:
    updates.append((code_w, nom_w, nom_c, nom))

c.executemany("""
    UPDATE facilities 
    SET wilaya_code = ?, wilaya = ?, commune = ?
    WHERE nom = ? AND (wilaya_code IS NULL OR wilaya_code = '' OR wilaya = 'nan')
""", updates)

conn.commit()

c.execute("SELECT count(*) FROM facilities WHERE wilaya_code != '' AND wilaya_code IS NOT NULL")
print(f"Total facilities avec wilaya_code valide : {c.fetchone()[0]}")

c.execute("SELECT count(*) FROM facilities WHERE wilaya_code = '27'")
print(f"Mostaganem total : {c.fetchone()[0]}")

conn.close()

