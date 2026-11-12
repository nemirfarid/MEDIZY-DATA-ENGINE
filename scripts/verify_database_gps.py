import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

wilayas = [
    ("Alger", "Exp: ~36.75, ~3.05"),
    ("Oran", "Exp: ~35.70, ~-0.63"),
    ("Constantine", "Exp: ~36.36, ~6.61"),
    ("Mostaganem", "Exp: ~35.93, ~0.09"),
    ("Ouargla", "Exp: ~31.95, ~5.32"),
    ("Ghardaïa", "Exp: ~32.49, ~3.67"),
    ("Tébessa", "Exp: ~35.40, ~8.12"),
    ("Tamanrasset", "Exp: ~22.78, ~5.52")
]

print("=== VERIFICATION DES COORDONNEES GPS PAR WILAYA ===")
for w_name, expected in wilayas:
    c.execute("SELECT count(*), avg(latitude), avg(longitude), min(latitude), max(latitude), min(longitude), max(longitude) FROM facilities WHERE wilaya = ?", (w_name,))
    cnt, alat, alon, minlat, maxlat, minlon, maxlon = c.fetchone()
    print(f"Wilaya {w_name:<12} | Total: {cnt:<5} | Centre GPS: ({alat:.4f}, {alon:.4f}) | {expected}")

print("\n=== RECHERCHE SPECIFIQUE SIDI ALI / BENTATA ===")
c.execute("SELECT nom, categorie, wilaya, commune, latitude, longitude FROM facilities WHERE (commune LIKE '%sidi ali%' OR nom LIKE '%sidi ali%' OR nom LIKE '%bentata%') AND wilaya = 'Mostaganem'")
for row in c.fetchall():
    print(row)

conn.close()
