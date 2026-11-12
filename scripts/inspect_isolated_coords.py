import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# Check coordinates of all structures
c.execute("SELECT id, nom, latitude, longitude, commune, wilaya FROM facilities")
all_facs = c.fetchall()

print(f"Total facilities to inspect: {len(all_facs)}")

# Let's detect isolated coordinates far from urban centers (> 40km from any wilaya chef-lieu or urban cluster)
WILAYAS = [
    ('01', 'Adrar', 27.8742, -0.2939),
    ('02', 'Chlef', 36.1652, 1.3345),
    ('03', 'Laghouat', 33.8000, 2.8651),
    ('04', 'Oum El Bouaghi', 35.8755, 7.1135),
    ('05', 'Batna', 35.5558, 6.1741),
    ('06', 'Béjaïa', 36.7559, 5.0843),
    ('07', 'Biskra', 34.8504, 5.7281),
    ('08', 'Béchar', 31.6167, -2.2167),
    ('09', 'Blida', 36.4700, 2.8300),
    ('10', 'Bouira', 36.3749, 3.9020),
    ('11', 'Tamanrasset', 22.7850, 5.5228),
    ('12', 'Tébessa', 35.4042, 8.1242),
    ('13', 'Tlemcen', 34.8828, -1.3167),
    ('14', 'Tiaret', 35.3710, 1.3170),
    ('15', 'Tizi Ouzou', 36.7118, 4.0459),
    ('16', 'Alger', 36.7538, 3.0588),
    ('17', 'Djelfa', 34.6728, 3.2630),
    ('18', 'Jijel', 36.8206, 5.7667),
    ('19', 'Sétif', 36.1911, 5.4137),
    ('20', 'Saïda', 34.8303, 0.1517),
    ('21', 'Skikda', 36.8792, 6.9075),
    ('22', 'Sidi Bel Abbès', 35.1899, -0.6309),
    ('23', 'Annaba', 36.9000, 7.7667),
    ('24', 'Guelma', 36.4621, 7.4261),
    ('25', 'Constantine', 36.3650, 6.6147),
    ('26', 'Médéa', 36.2642, 2.7539),
    ('27', 'Mostaganem', 35.9311, 0.0892),
    ('28', "M'Sila", 35.7058, 4.5419),
    ('29', 'Mascara', 35.3964, 0.1403),
    ('30', 'Ouargla', 31.9493, 5.3250),
    ('31', 'Oran', 35.6971, -0.6308),
    ('32', 'El Bayadh', 33.6832, 1.0193),
    ('33', 'Illizi', 26.4833, 8.4667),
    ('34', 'Bordj Bou Arreridj', 36.0732, 4.7611),
    ('35', 'Boumerdès', 36.7664, 3.4772),
    ('36', 'El Tarf', 36.7672, 8.3138),
    ('37', 'Tindouf', 27.6711, -8.1474),
    ('38', 'Tissemsilt', 35.6072, 1.8108),
    ('39', 'El Oued', 33.3683, 6.8675),
    ('40', 'Khenchela', 35.4358, 7.1433),
    ('41', 'Souk Ahras', 36.2864, 7.9511),
    ('42', 'Tipaza', 36.5897, 2.4475),
    ('43', 'Mila', 36.4503, 6.2644),
    ('44', 'Aïn Defla', 36.2644, 1.9675),
    ('45', 'Naâma', 33.2667, -0.3167),
    ('46', 'Aïn Témouchent', 35.2975, -1.1403),
    ('47', 'Ghardaïa', 32.4909, 3.6736),
    ('48', 'Relizane', 35.7372, 0.5558),
    ('49', 'Timimoun', 29.2639, 0.2310),
    ('50', 'Bordj Badji Mokhtar', 21.3283, 0.9547),
    ('51', 'Ouled Djellal', 34.4278, 5.0667),
    ('52', 'Béni Abbès', 30.1333, -2.1667),
    ('53', 'In Salah', 27.1936, 2.4608),
    ('54', 'In Guezzam', 19.5667, 5.7667),
    ('55', 'Touggourt', 33.1053, 6.0578),
    ('56', 'Djanet', 24.5531, 9.4853),
    ('57', "El M'Ghair", 33.9500, 5.9167),
    ('58', 'El Meniaa', 30.5847, 2.8797),
]

# Check any facilities with 0.0, 0.0 or suspicious round coordinates
c.execute("SELECT id, nom, latitude, longitude FROM facilities WHERE latitude = 0 OR longitude = 0 OR (latitude = round(latitude, 1) AND longitude = round(longitude, 1))")
rounded = c.fetchall()
print(f"Facilities with flat rounded coordinates: {len(rounded)}")
for r in rounded[:10]:
    print("  ", r)

conn.close()

