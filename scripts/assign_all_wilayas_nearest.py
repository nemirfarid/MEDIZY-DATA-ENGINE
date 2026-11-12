import sqlite3
import math

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

WILAYA_CENTERS = [
    ("01", "Adrar", 27.8742, -0.2939),
    ("02", "Chlef", 36.1652, 1.3345),
    ("03", "Laghouat", 33.8000, 2.8651),
    ("04", "Oum El Bouaghi", 35.8755, 7.1135),
    ("05", "Batna", 35.5558, 6.1741),
    ("06", "Béjaïa", 36.7559, 5.0843),
    ("07", "Biskra", 34.8504, 5.7281),
    ("08", "Béchar", 31.6167, -2.2167),
    ("09", "Blida", 36.4700, 2.8300),
    ("10", "Bouira", 36.3749, 3.9020),
    ("11", "Tamanrasset", 22.7850, 5.5228),
    ("12", "Tébessa", 35.4042, 8.1242),
    ("13", "Tlemcen", 34.8783, -1.3150),
    ("14", "Tiaret", 35.3710, 1.3169),
    ("15", "Tizi Ouzou", 36.7118, 4.0459),
    ("16", "Alger", 36.7538, 3.0588),
    ("17", "Djelfa", 34.6728, 3.2630),
    ("18", "Jijel", 36.8205, 5.7667),
    ("19", "Sétif", 36.1911, 5.4137),
    ("20", "Saïda", 34.8303, 0.1517),
    ("21", "Skikda", 36.8792, 6.9075),
    ("22", "Sidi Bel Abbès", 35.1899, -0.6308),
    ("23", "Annaba", 36.9000, 7.7667),
    ("24", "Guelma", 36.4621, 7.4261),
    ("25", "Constantine", 36.3650, 6.6147),
    ("26", "Médéa", 36.2642, 2.7539),
    ("27", "Mostaganem", 35.9311, 0.0892),
    ("28", "M'Sila", 35.7058, 4.5419),
    ("29", "Mascara", 35.3964, 0.1403),
    ("30", "Ouargla", 31.9493, 5.3250),
    ("31", "Oran", 35.6976, -0.6337),
    ("32", "El Bayadh", 33.6832, 1.0193),
    ("33", "Illizi", 26.4833, 8.4667),
    ("34", "Bordj Bou Arreridj", 36.0732, 4.7611),
    ("35", "Boumerdes", 36.7599, 3.4728),
    ("36", "El Tarf", 36.7672, 8.3138),
    ("37", "Tindouf", 27.6711, -8.1474),
    ("38", "Tissemsilt", 35.6072, 1.8108),
    ("39", "El Oued", 33.3683, 6.8674),
    ("40", "Khenchela", 35.4358, 7.1433),
    ("41", "Souk Ahras", 36.2864, 7.9511),
    ("42", "Tipaza", 36.5897, 2.4475),
    ("43", "Mila", 36.4503, 6.2644),
    ("44", "Aïn Defla", 36.2644, 1.9678),
    ("45", "Naâma", 33.2667, -0.3167),
    ("46", "Aïn Témouchent", 35.2975, -1.1404),
    ("47", "Ghardaïa", 32.4909, 3.6735),
    ("48", "Relizane", 35.7373, 0.5558),
    ("49", "El M'Ghair", 33.9500, 5.9200),
    ("50", "El Meniaa", 30.5833, 2.8833),
    ("51", "Ouled Djellal", 34.4333, 5.0667),
    ("52", "Bordj Badji Mokhtar", 21.3283, 0.9547),
    ("53", "Béni Abbès", 30.1333, -2.1667),
    ("54", "Timimoun", 29.2639, 0.2310),
    ("55", "Touggourt", 33.1053, 6.0578),
    ("56", "Djanet", 24.5536, 9.4853),
    ("57", "In Salah", 27.1936, 2.4608),
    ("58", "In Guezzam", 19.5722, 5.7694)
]

def find_nearest_wilaya(lat, lon):
    best_w = WILAYA_CENTERS[0]
    min_dist = float('inf')
    for w in WILAYA_CENTERS:
        # Distance euclidienne pondérée en coordonnées
        d = (lat - w[2])**2 + ((lon - w[3]) * math.cos(math.radians(lat)))**2
        if d < min_dist:
            min_dist = d
            best_w = w
    return best_w[0], best_w[1]

# Charger toutes les structures sans wilaya
c.execute("""
    SELECT id, latitude, longitude, adresse 
    FROM facilities 
    WHERE wilaya_code IS NULL OR wilaya_code = '' OR wilaya = 'nan'
""")
rows = c.fetchall()
print(f"Assignation de la wilaya pour {len(rows)} structures réelles...")

updates = []
for fid, lat, lon, addr in rows:
    code, name = find_nearest_wilaya(lat, lon)
    # Tenter d'extraire la commune si elle figure dans l'adresse
    commune = name
    if addr and addr != 'nan':
        parts = [p.strip() for p in addr.split(',') if p.strip()]
        if parts:
            last = parts[-1]
            if len(parts) >= 2:
                commune = parts[-2]
            else:
                commune = last
    updates.append((code, name, commune, fid))

c.executemany("""
    UPDATE facilities 
    SET wilaya_code = ?, wilaya = ?, commune = ?
    WHERE id = ?
""", updates)

conn.commit()

c.execute("SELECT count(*) FROM facilities WHERE wilaya_code IS NOT NULL AND wilaya_code != ''")
print(f"Total assigné avec succès : {c.fetchone()[0]}")

c.execute("SELECT wilaya_code, wilaya, count(*) FROM facilities GROUP BY wilaya_code ORDER BY cast(wilaya_code as integer) LIMIT 10")
print("Échantillon :", c.fetchall())

conn.close()

