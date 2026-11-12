import sqlite3

con = sqlite3.connect('assets/data/sante_dz_bundled.db')
cur = con.cursor()

total = cur.execute("SELECT count(*) FROM facilities").fetchone()[0]
print("Total facilities in bundled DB:", total)

# Vérifier coordonnées hors Algérie
out_of_bounds = cur.execute("""
SELECT count(*) FROM facilities 
WHERE latitude NOT BETWEEN 18.9 AND 37.5 
   OR longitude NOT BETWEEN -8.7 AND 12.0
""").fetchone()[0]
print("Out of Algeria bounds:", out_of_bounds)

# Vérifier cluster artificiel 33.3, 5.7
cluster_33 = cur.execute("""
SELECT count(*) FROM facilities 
WHERE latitude BETWEEN 33.28 AND 33.32 
  AND longitude BETWEEN 5.68 AND 5.72 
  AND wilaya_code NOT IN ('39', '55', '57')
""").fetchone()[0]
print("Artificial 33.3, 5.7 cluster (northern wilayas):", cluster_33)

# Vérifier Sidi Ali Mostaganem
sidi_ali = cur.execute("""
SELECT count(*), min(latitude), max(latitude), min(longitude), max(longitude)
FROM facilities 
WHERE commune = 'Sidi Ali'
""").fetchone()
print(f"Sidi Ali ({sidi_ali[0]} structures): Lat [{sidi_ali[1]} à {sidi_ali[2]}], Lon [{sidi_ali[3]} à {sidi_ali[4]}]")

# Vérifier Bentata
bentata = cur.execute("SELECT id, nom, commune, wilaya, latitude, longitude FROM facilities WHERE nom LIKE '%bentata%' AND commune = 'Sidi Ali'").fetchall()
print("Dr Bentata in Sidi Ali:", bentata)

# Échantillon wilayas
print("\nÉchantillon de coordonnées réelles par Wilaya :")
for wcode in ['16', '31', '25', '27', '06', '09']:
    sample = cur.execute(f"SELECT wilaya, commune, nom, latitude, longitude FROM facilities WHERE wilaya_code = '{wcode}' LIMIT 1").fetchone()
    print(f"  Wilaya {wcode} ({sample[0]}): {sample[2]} ({sample[1]}) -> GPS: ({sample[3]}, {sample[4]})")

