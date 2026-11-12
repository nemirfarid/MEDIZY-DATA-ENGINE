import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

c.execute("SELECT id, nom, categorie, commune, latitude, longitude, adresse FROM facilities WHERE wilaya_code = '01' ORDER BY commune, categorie, nom")
rows = c.fetchall()

print(f"=== WILAYA 01 - ADRAR : INVENTAIRE DÉTAILLÉ ({len(rows)} STRUCTURES RÉELLES) ===")
current_commune = ""
current_cat = ""
for r in rows:
    fac_id, nom, cat, com, lat, lon, addr = r
    if com != current_commune:
        current_commune = com
        print(f"\n==========================================")
        print(f"COMMUNE : {current_commune.upper()}")
        print(f"==========================================")
    if cat != current_cat:
        current_cat = cat
        print(f"\n  [Catégorie : {current_cat}]")
    print(f"    * {nom} -> GPS: ({lat:.6f}, {lon:.6f}) | Réf: {addr}")

conn.close()

