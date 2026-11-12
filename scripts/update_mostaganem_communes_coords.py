import sqlite3

# Accurate centroids for all 32 official communes of Mostaganem (Wilaya 27)
MOSTAGANEM_COMMUNES_CORRECTED = {
    '2701': ('Achaacha', 36.2450, 0.6350),
    '2702': ('Khadra', 36.2350, 0.5560),
    '2703': ('Nekmaria', 36.1820, 0.6300),
    '2704': ('Ouled Boughalem', 36.2940, 0.6980),
    '2705': ('Ain-Nouissy', 35.8000, 0.0500),
    '2706': ('Fornaka', 35.7517, -0.0161),
    '2707': ('Hassiane', 35.7537, 0.1202),
    '2708': ('Ain-Tedles', 35.9660, 0.2520),
    '2709': ('Oued El Kheir', 35.9440, 0.3850),
    '2710': ('Sidi Belaattar', 35.9570, 0.3180),
    '2711': ('Sour', 35.9620, 0.3160),
    '2712': ('Bouguirat', 35.7700, 0.2480),
    '2713': ('Safsaf', 35.8440, 0.3790),
    '2714': ('Sirat', 35.7370, 0.1720),
    '2715': ('Souaflia', 35.8500, 0.3130),
    '2716': ('Hassi Mameche', 35.8210, 0.0200),
    '2717': ('Mazagran', 35.8900, 0.0710),
    '2718': ('Stidia', 35.8333, 0.0000),
    '2719': ('Ain-Boudinar', 35.9930, 0.2150),
    '2720': ('Kheir-Eddine', 35.9540, 0.1810),
    '2721': ('Sayada', 35.9514, 0.1308),
    '2722': ('Ain-Sidi Cherif', 35.8180, 0.1410),
    '2723': ('Mansourah', 35.8434, 0.2315),
    '2724': ('Mesra', 35.8460, 0.1770),
    '2725': ('Touahria', 35.8120, 0.2190),
    '2726': ('Mostaganem', 35.9312, 0.0892), # True downtown chef-lieu
    '2727': ('Ouled-Maalah', 36.0460, 0.5920),
    '2728': ('Sidi Ali', 36.1012, 0.4145),
    '2729': ('Tazgait', 36.1310, 0.5440),
    '2730': ('Benabdelmalek Ramdane', 36.1530, 0.3870),
    '2731': ('Hadjadj', 36.0959, 0.3251),
    '2732': ('Sidi-Lakhdar', 36.1671, 0.4384)
}

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

for cid, (cname, lat, lon) in MOSTAGANEM_COMMUNES_CORRECTED.items():
    c.execute("UPDATE communes SET latitude = ?, longitude = ? WHERE id = ? OR (wilaya_code = '27' AND nom_fr = ?)", (lat, lon, cid, cname))

conn.commit()
print("Updated all 32 commune coordinates in Mostaganem.")

