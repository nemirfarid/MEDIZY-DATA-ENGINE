"""
Vérification que les coordonnées ne sont jamais inventées.
Toutes les coordonnées GPS doivent provenir de Nominatim ou être NULL.
"""

import sqlite3

# Check synthetic DB
synth = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper_synthetic.db')
c = synth.cursor()

print("=" * 80)
print("VÉRIFICATION COORDONNÉES NON INVENTÉES — BASE SYNTHÉTIQUE")
print("=" * 80)

c.execute("""
    SELECT id, place_id, nom, wilaya, latitude, longitude, source, commune_source
    FROM places 
    WHERE source = 'MIPH_2025_SYNTH'
    ORDER BY id
""")
rows = c.fetchall()

for r in rows:
    id_, place_id, nom, wilaya, lat, lon, source, commune_source = r
    if lat is not None and lon is not None:
        print(f"  ID {id_} | {place_id} | {nom} | GPS=({lat:.6f}, {lon:.6f}) | source={source} | commune_source={commune_source}")
        if commune_source.startswith('NOMINATIM'):
            print(f"    OK Coordonnées depuis Nominatim (valide)")
        else:
            print(f"    WARNING Source inattendue: {commune_source}")
    else:
        print(f"  ID {id_} | {place_id} | {nom} | GPS=NULL | source={source} | commune_source={commune_source}")
        if commune_source == 'MIPH_2025_SYNTH':
            print(f"    OK GPS NULL car code_postal=0 ou echec geocodage (non invente)")
        else:
            print(f"    OK GPS NULL (echec geocodage legitime)")

synth.close()

# Check production DB for MIPH_2025 entries
print("\n" + "=" * 80)
print("VÉRIFICATION COORDONNÉES NON INVENTÉES — BASE PRODUCTION (MIPH_2025)")
print("=" * 80)

prod = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = prod.cursor()

c.execute("""
    SELECT id, place_id, nom, wilaya, latitude, longitude, source, commune_source
    FROM places 
    WHERE source = 'MIPH_2025'
    ORDER BY id
""")
rows = c.fetchall()

nominatim_count = 0
null_count = 0
other_count = 0

for r in rows:
    id_, place_id, nom, wilaya, lat, lon, source, commune_source = r
    if lat is not None and lon is not None:
        if commune_source and commune_source.startswith('NOMINATIM'):
            nominatim_count += 1
            print(f"  ID {id_} | {place_id} | GPS=({lat:.6f}, {lon:.6f}) | {commune_source} OK")
        else:
            other_count += 1
            print(f"  ID {id_} | {place_id} | GPS=({lat:.6f}, {lon:.6f}) | source={commune_source} WARNING")
    else:
        null_count += 1
        print(f"  ID {id_} | {place_id} | GPS=NULL | {commune_source} OK")

print(f"\nResume MIPH_2025 production:")
print(f"  Coordonnees depuis Nominatim: {nominatim_count}")
print(f"  GPS NULL (non invente): {null_count}")
print(f"  Autres sources: {other_count}")
print(f"  Total: {len(rows)}")

if other_count == 0:
    print("  OK AUCUNE coordonnee inventee - toutes proviennent de Nominatim ou sont NULL")
else:
    print(f"  WARNING {other_count} entrees avec source de coordonnees non Nominatim")

prod.close()