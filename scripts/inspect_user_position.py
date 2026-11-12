import pandas as pd
import sqlite3

# Check row 22558 of Excel
df = pd.read_excel('RAPPORT_ALIGNEMENT_MEDIZY_GOOGLE_MAPS_1541_COMMUNES_OFFICIEL.xlsx')
row_idx = 22556 # around line 22558 (accounting for 1-based index and header)
print("=== Lines 22555 to 22562 of Excel ===")
print(df.iloc[22554:22560][['Wilaya', 'Commune', 'Nom de la structure ou praticien Google Maps', 'Coordonnées GPS Google Maps', 'Coordonnées GPS Medizy', 'Distance (mètres)', 'Distance < 1 mètre', 'Statut / Action Medizy']])

print("\n=== Inspecting medizy_scraper.db ===")
try:
    conn = sqlite3.connect('medizy_scraper.db')
    cursor = conn.cursor()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for t in tables:
        cnt = cursor.execute(f"SELECT count(*) FROM {t[0]}").fetchone()[0]
        print(f"Table {t[0]}: {cnt} rows")
        cols = [c[1] for c in cursor.execute(f"PRAGMA table_info({t[0]})").fetchall()]
        print(f"  Columns: {cols[:8]}")
    conn.close()
except Exception as e:
    print("Error medizy_scraper.db:", e)

print("\n=== Inspecting bundled db ===")
try:
    conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
    cursor = conn.cursor()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for t in tables:
        cnt = cursor.execute(f"SELECT count(*) FROM {t[0]}").fetchone()[0]
        print(f"Table {t[0]}: {cnt} rows")
    conn.close()
except Exception as e:
    print("Error bundled db:", e)

