"""
Phase 6.2 - Étape A : Mesure des lacunes
Analyse complète de la base de production actuelle.
"""

import sqlite3
import csv
from collections import Counter

DB_PATH = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("=" * 80)
print("PHASE 6.2 - ÉTAPE A : MESURE DES LACUNES")
print("=" * 80)

# 1. Statistiques globales
c.execute('SELECT COUNT(*) FROM places;')
total = c.fetchone()[0]
print(f"\n1. TOTAL ÉTABLISSEMENTS: {total}")

# Par source
c.execute('SELECT source, COUNT(*) FROM places GROUP BY source ORDER BY COUNT(*) DESC;')
print("\n2. RÉPARTITION PAR SOURCE:")
for row in c.fetchall():
    print(f"   {row[0]}: {row[1]}")

# Par wilaya
c.execute('SELECT wilaya, COUNT(*) FROM places GROUP BY wilaya ORDER BY COUNT(*) DESC;')
wilaya_counts = c.fetchall()
print("\n3. RÉPARTITION PAR WILAYA (top 10 / bottom 10):")
print("   TOP 10:")
for row in wilaya_counts[:10]:
    print(f"      {row[0]}: {row[1]}")
print("   BOTTOM 10:")
for row in wilaya_counts[-10:]:
    print(f"      {row[0]}: {row[1]}")

# Par catégorie
c.execute('SELECT categorie_recherche, COUNT(*) FROM places GROUP BY categorie_recherche ORDER BY COUNT(*) DESC;')
print("\n4. RÉPARTITION PAR CATÉGORIE:")
for row in c.fetchall():
    print(f"   {row[0]}: {row[1]}")

# Par commune (top 20)
c.execute('SELECT commune, wilaya, COUNT(*) FROM places WHERE commune IS NOT NULL AND commune != "" GROUP BY commune, wilaya ORDER BY COUNT(*) DESC LIMIT 20;')
print("\n5. TOP 20 COMMUNES:")
for row in c.fetchall():
    print(f"   {row[0]} ({row[1]}): {row[2]}")

# 6. Communes sans établissements
c.execute('''
    SELECT c.nom_fr, c.wilaya_code, w.nom_fr
    FROM communes c
    JOIN wilayas w ON c.wilaya_code = w.code
    LEFT JOIN places p ON p.commune = c.nom_fr AND p.wilaya_normalized = w.nom_fr
    WHERE p.id IS NULL
''')
communes_vides = c.fetchall()
print(f"\n6. COMMUNES SANS AUCUN ÉTABLISSEMENT: {len(communes_vides)}")
# Afficher par wilaya
wilaya_vides = Counter()
for cv in communes_vides:
    wilaya_vides[cv[2]] += 1
print("   Par wilaya (top 10):")
for wilaya, count in wilaya_vides.most_common(10):
    print(f"      {wilaya}: {count} communes vides")

# 7. Établissements sans téléphone, adresse, site, horaires
c.execute('SELECT COUNT(*) FROM places WHERE telephone IS NULL OR telephone = "";')
sans_tel = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM places WHERE adresse IS NULL OR adresse = "";')
sans_adresse = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM places WHERE site_web IS NULL OR site_web = "";')
sans_site = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM places WHERE horaires IS NULL OR horaires = "";')
sans_horaires = c.fetchone()[0]

print(f"\n7. DONNÉES MANQUANTES:")
print(f"   Sans téléphone: {sans_tel} ({sans_tel/total*100:.1f}%)")
print(f"   Sans adresse: {sans_adresse} ({sans_adresse/total*100:.1f}%)")
print(f"   Sans site web: {sans_site} ({sans_site/total*100:.1f}%)")
print(f"   Sans horaires: {sans_horaires} ({sans_horaires/total*100:.1f}%)")

# 8. Couverture GPS
c.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL;')
avec_gps = c.fetchone()[0]
print(f"   Avec GPS: {avec_gps} ({avec_gps/total*100:.1f}%)")

# 9. Analyse détaillée BISKRA (wilaya_code = 5)
print("\n" + "=" * 80)
print("ANALYSE DÉTAILLÉE BISKRA (wilaya_code=5)")
print("=" * 80)

c.execute('SELECT COUNT(*) FROM places WHERE wilaya = "Biskra" OR wilaya_normalized = "biskra";')
biskra_total = c.fetchone()[0]
print(f"\nTotal établissements Biskra: {biskra_total}")

# Par catégorie à Biskra
c.execute('''
    SELECT categorie_recherche, COUNT(*) 
    FROM places 
    WHERE wilaya = "Biskra" OR wilaya_normalized = "biskra"
    GROUP BY categorie_recherche 
    ORDER BY COUNT(*) DESC
''')
print("\nPar catégorie à Biskra:")
biskra_cats = c.fetchall()
for row in biskra_cats:
    print(f"   {row[0]}: {row[1]}")

# Par commune à Biskra
c.execute('''
    SELECT commune, COUNT(*) 
    FROM places 
    WHERE (wilaya = "Biskra" OR wilaya_normalized = "biskra") 
    AND commune IS NOT NULL AND commune != ""
    GROUP BY commune 
    ORDER BY COUNT(*) DESC
''')
print("\nPar commune à Biskra:")
biskra_communes = c.fetchall()
for row in biskra_communes:
    print(f"   {row[0]}: {row[1]}")

# Communes de Biskra (depuis table communes)
c.execute('SELECT nom_fr FROM communes WHERE wilaya_code = "5" ORDER BY nom_fr;')
biskra_all_communes = [row[0] for row in c.fetchall()]
print(f"\nTotal communes officielles Biskra: {len(biskra_all_communes)}")
biskra_covered_communes = set(row[0] for row in biskra_communes)
biskra_missing_communes = [c for c in biskra_all_communes if c not in biskra_covered_communes]
print(f"Communes couvertes: {len(biskra_covered_communes)}")
print(f"Communes SANS établissement: {len(biskra_missing_communes)}")
if biskra_missing_communes:
    print(f"   Communes manquantes: {', '.join(biskra_missing_communes[:20])}")
    if len(biskra_missing_communes) > 20:
        print(f"   ... et {len(biskra_missing_communes) - 20} autres")

# Catégories manquantes à Biskra (comparé au niveau national)
c.execute('SELECT DISTINCT categorie_recherche FROM places;')
all_cats = set(row[0] for row in c.fetchall())
biskra_cats_set = set(row[0] for row in biskra_cats)
missing_cats_biskra = all_cats - biskra_cats_set
print(f"\nCatégories nationales: {len(all_cats)}")
print(f"Catégories présentes à Biskra: {len(biskra_cats_set)}")
print(f"Catégories MANQUANTES à Biskra: {len(missing_cats_biskra)}")
if missing_cats_biskra:
    for cat in sorted(missing_cats_biskra):
        # Compter nationalement
        c.execute('SELECT COUNT(*) FROM places WHERE categorie_recherche = ?', (cat,))
        nat_count = c.fetchone()[0]
        print(f"   {cat} (national: {nat_count})")

# 10. Établissements Biskra sans téléphone/adresse
c.execute('''
    SELECT COUNT(*) FROM places 
    WHERE (wilaya = "Biskra" OR wilaya_normalized = "biskra")
    AND (telephone IS NULL OR telephone = "")
''')
biskra_sans_tel = c.fetchone()[0]
c.execute('''
    SELECT COUNT(*) FROM places 
    WHERE (wilaya = "Biskra" OR wilaya_normalized = "biskra")
    AND (adresse IS NULL OR adresse = "")
''')
biskra_sans_adresse = c.fetchone()[0]

print(f"\nBiskra - Sans téléphone: {biskra_sans_tel}/{biskra_total} ({biskra_sans_tel/biskra_total*100:.1f}%)")
print(f"Biskra - Sans adresse: {biskra_sans_adresse}/{biskra_total} ({biskra_sans_adresse/biskra_total*100:.1f}%)")

# 11. Sources pour Biskra
c.execute('''
    SELECT source, COUNT(*) 
    FROM places 
    WHERE wilaya = "Biskra" OR wilaya_normalized = "biskra"
    GROUP BY source 
    ORDER BY COUNT(*) DESC
''')
print("\nSources à Biskra:")
for row in c.fetchall():
    print(f"   {row[0]}: {row[1]}")

conn.close()

print("\n" + "=" * 80)
print("FIN MESURE DES LACUNES")
print("=" * 80)