"""
Comparaison exhaustive des métriques de la base de production
avant et après les tests (doit être identique).
"""

import sqlite3
import hashlib

def get_db_metrics(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    
    metrics = {}
    
    # Total places
    c.execute('SELECT COUNT(*) FROM places;')
    metrics['total_places'] = c.fetchone()[0]
    
    # MIPH_2025 count
    c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025';")
    metrics['miph_2025'] = c.fetchone()[0]
    
    # MIPH_2025_SYNTH count
    c.execute("SELECT COUNT(*) FROM places WHERE source = 'MIPH_2025_SYNTH';")
    metrics['miph_2025_synth'] = c.fetchone()[0]
    
    # GPS coverage
    c.execute('SELECT COUNT(*) FROM places WHERE latitude IS NOT NULL AND longitude IS NOT NULL;')
    metrics['with_gps'] = c.fetchone()[0]
    
    # Phone coverage
    c.execute('SELECT COUNT(*) FROM places WHERE telephone IS NOT NULL AND telephone != "";')
    metrics['with_phone'] = c.fetchone()[0]
    
    # Place_id unique
    c.execute('SELECT COUNT(*) FROM places WHERE place_id IS NOT NULL;')
    total_ids = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT place_id) FROM places WHERE place_id IS NOT NULL;')
    unique_ids = c.fetchone()[0]
    metrics['place_id_total'] = total_ids
    metrics['place_id_unique'] = unique_ids
    metrics['place_id_unique_ok'] = total_ids == unique_ids
    
    # google_maps_url unique
    c.execute('SELECT COUNT(*) FROM places WHERE google_maps_url IS NOT NULL;')
    total_gmaps = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT google_maps_url) FROM places WHERE google_maps_url IS NOT NULL;')
    unique_gmaps = c.fetchone()[0]
    metrics['gmaps_total'] = total_gmaps
    metrics['gmaps_unique'] = unique_gmaps
    metrics['gmaps_unique_ok'] = total_gmaps == unique_gmaps
    
    # Wilaya distribution
    c.execute('SELECT wilaya, COUNT(*) FROM places GROUP BY wilaya ORDER BY wilaya;')
    metrics['wilaya_dist'] = dict(c.fetchall())
    
    # Category distribution
    c.execute('SELECT categorie_recherche, COUNT(*) FROM places GROUP BY categorie_recherche ORDER BY categorie_recherche;')
    metrics['category_dist'] = dict(c.fetchall())
    
    # Integrity
    c.execute('PRAGMA integrity_check;')
    metrics['integrity'] = c.fetchone()[0]
    
    conn.close()
    return metrics

def compute_hash(path):
    """Compute SHA256 of database file."""
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

print("=" * 80)
print("COMPARAISON BASE PRODUCTION AVANT/APRÈS TESTS")
print("=" * 80)

# Current production metrics
prod_path = r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db'
backup_path = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_audit_20261011_021419.db'

prod_metrics = get_db_metrics(prod_path)
backup_metrics = get_db_metrics(backup_path)

# File hashes
prod_hash = compute_hash(prod_path)
backup_hash = compute_hash(backup_path)

print(f"\nHash fichier production:  {prod_hash}")
print(f"Hash fichier backup:      {backup_hash}")
print(f"Fichiers identiques: {prod_hash == backup_hash}")

print("\n--- MÉTRIQUES PRODUCTION ---")
for k, v in prod_metrics.items():
    if k not in ('wilaya_dist', 'category_dist'):
        print(f"  {k}: {v}")

print("\n--- MÉTRIQUES BACKUP ---")
for k, v in backup_metrics.items():
    if k not in ('wilaya_dist', 'category_dist'):
        print(f"  {k}: {v}")

print("\n--- COMPARAISON ---")
all_match = True
for k in prod_metrics:
    if k not in ('wilaya_dist', 'category_dist'):
        match = prod_metrics[k] == backup_metrics[k]
        status = "OK" if match else "DIFFERENT"
        if not match:
            all_match = False
        print(f"  {k}: prod={prod_metrics[k]} vs backup={backup_metrics[k]} [{status}]")

# Check wilaya distribution
print("\n--- DISTRIBUTION WILAYA (échantillon) ---")
wilaya_match = prod_metrics['wilaya_dist'] == backup_metrics['wilaya_dist']
print(f"  Identique: {wilaya_match}")
if not wilaya_match:
    all_match = False
    for w in set(list(prod_metrics['wilaya_dist'].keys()) + list(backup_metrics['wilaya_dist'].keys())):
        pc = prod_metrics['wilaya_dist'].get(w, 0)
        bc = backup_metrics['wilaya_dist'].get(w, 0)
        if pc != bc:
            print(f"    {w}: prod={pc} vs backup={bc}")

# Check category distribution
print("\n--- DISTRIBUTION CATÉGORIE (échantillon) ---")
cat_match = prod_metrics['category_dist'] == backup_metrics['category_dist']
print(f"  Identique: {cat_match}")
if not cat_match:
    all_match = False

print("\n" + "=" * 80)
if all_match and prod_hash == backup_hash:
    print("RESULTAT: OK BASE DE PRODUCTION INCHANGEE")
    print("  - Hash fichier identique")
    print("  - Toutes les metriques identiques")
    print("  - Distribution wilaya/categorie identiques")
    print("  - Integrite SQLite OK")
else:
    print("RESULTAT: FAIL BASE DE PRODUCTION MODIFIEE")
    print("  - Differences detectees")
print("=" * 80)