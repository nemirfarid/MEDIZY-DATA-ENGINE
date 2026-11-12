import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# 1. Update Laboratoire Dr Ouzani
c.execute("""
    UPDATE facilities 
    SET nom = 'Laboratoire d''Analyses Médicales Dr. Chahinaze Ouzani (مخبر التحاليل الطبية الدكتورة وزاني)',
        categorie = 'Laboratoire d''analyse médicale'
    WHERE id = 76287
""")

# 2. Update El Anis Dental Clinic (Dr Ali Lazergui)
c.execute("""
    UPDATE facilities 
    SET nom = 'El Anis Dental Clinic - Dr. Ali Lazergui (عيادة الأنيس لطب الأسنان)',
        categorie = 'Dentiste',
        adresse = 'Route 1er Novembre (2ème bâtiment à côté de Fekir Clinic), Sidi Ali',
        telephone = '0552 26 38 88',
        latitude = 36.0972,
        longitude = 0.4136
    WHERE id = 101864
""")

c.execute('UPDATE facilities_rtree SET min_lat = 36.0972, max_lat = 36.0972, min_lon = 0.4136, max_lon = 0.4136 WHERE id = 101864')

# 3. Clean any generic place_id names across all 1541 communes
# E.g. where nom was just "Laboratoire d'analyse médicale", "Cabinet médical", "Médecin", "Dentiste", etc.
# Check how many generic names exist in database:
c.execute("SELECT count(*) FROM facilities WHERE nom IN ('Laboratoire d''analyse médicale', 'Cabinet médical', 'Médecin', 'Dentiste', 'Pharmacie', 'Clinique')")
generic_count = c.fetchone()[0]
print(f'Structures with strictly generic names: {generic_count}')

conn.commit()
print('Updated Dr Ouzani Lab and El Anis Dental Clinic!')
conn.close()

