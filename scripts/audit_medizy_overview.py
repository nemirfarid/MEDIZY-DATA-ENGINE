import pandas as pd
import sqlite3

# 1. Check Excel line around 25396
try:
    df = pd.read_excel('RAPPORT_ALIGNEMENT_MEDIZY_GOOGLE_MAPS_1541_COMMUNES.xlsx')
    print("=== Row 25390 to 25400 of Excel ===")
    print(df.iloc[25390:25402][['Wilaya', 'Commune', 'Nom de la structure ou praticien Google Maps', 'Coordonnées GPS Google Maps', 'Nom de la structure Medizy', 'Coordonnées GPS Medizy', 'Distance (mètres)', 'Distance < 1 mètre', 'Statut / Action Medizy']].to_string())
except Exception as e:
    print("Error reading excel:", e)

# 2. Check bundled DB metrics
try:
    conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
    c = conn.cursor()
    c.execute("SELECT count(*) FROM facilities")
    total_fac = c.fetchone()[0]
    
    c.execute("SELECT count(DISTINCT wilaya), count(DISTINCT commune) FROM facilities")
    wils, coms = c.fetchone()
    
    c.execute("SELECT categorie, count(*) FROM facilities GROUP BY categorie ORDER BY count(*) DESC LIMIT 10")
    top_cats = c.fetchall()
    
    c.execute("SELECT count(*) FROM facilities WHERE telephone IS NOT NULL AND length(trim(telephone)) > 0")
    with_phone = c.fetchone()[0]
    
    c.execute("SELECT count(*) FROM facilities WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    with_gps = c.fetchone()[0]
    
    print("\n=== Bundled DB Facilities ===")
    print(f"Total facilities: {total_fac}")
    print(f"Distinct Wilayas: {wils}, Distinct Communes: {coms}")
    print(f"With GPS: {with_gps} ({with_gps/total_fac*100:.1f}%)")
    print(f"With Phone: {with_phone} ({with_phone/total_fac*100:.1f}%)")
    print("Top categories:", top_cats)
    
    conn.close()
except Exception as e:
    print("Error db:", e)

