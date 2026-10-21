#!/usr/bin/env python3
"""Check for error-artifact entries in the checkpoint and recovered entries."""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Keywords that indicate error artifacts
error_keywords = [
    'impossible d',
    'erreur',
    'connexion',
    'aucun résultat',
    'non disponible',
    'captcha',
    'timeout',
    'page introuvable',
    'accès refusé',
    'service indisponible',
]

def is_error_artifact(name, address):
    """Check if an entry is an error artifact."""
    text = (name + ' ' + address).lower().strip()
    for kw in error_keywords:
        if kw in text:
            return True
    return False

# Check checkpoint
with open(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

artifacts = []
for r in rows:
    nom = r.get('nom', '').strip()
    adr = r.get('adresse', '').strip()
    if is_error_artifact(nom, adr):
        artifacts.append(r)

print(f"=== ANALYSE DES ARTÉFACTS D'ERREUR ===")
print(f"Total rows dans checkpoint: {len(rows)}")
print(f"Artéfacts d'erreur détectés: {len(artifacts)}")

# Show details
for a in artifacts[:5]:
    print(f"\n  Nom: {a.get('nom', '')}")
    print(f"  Wilaya: {a.get('wilaya', '')}")
    print(f"  Catégorie: {a.get('categorie_recherche', '')}")
    print(f"  Adresse: {a.get('adresse', '')}")
    print(f"  Téléphone: {a.get('telephone', '')}")
    print(f"  Note: {a.get('note', '')}")
    print(f"  GPS: {a.get('latitude', '')}, {a.get('longitude', '')}")
    print(f"  URL: {a.get('google_maps_url', '')[:80]}")
    print(f"  Source: {a.get('source', '')}")
    print(f"  Date scrape: {a.get('scrape_date', '')}")

# Check if any of the 24 new entries are artifacts
print("\n=== VÉRIFICATION DES 24 ENTRÉES RÉcupérées ===")
artifact_pids = set(a.get('place_id_si_visible', '').strip() for a in artifacts)
artifact_urls = set(a.get('google_maps_url', '').strip() for a in artifacts)

recovered_artifacts = [a for a in artifacts if a.get('source', '') == 'Google Maps public UI']
print(f"Artéfacts parmi les entrées récupérées: {len(recovered_artifacts)}")

# Check for entries with empty nom but valid other fields
empty_name = [r for r in rows if not r.get('nom', '').strip() and (r.get('telephone', '').strip() or r.get('latitude', '').strip())]
print(f"\nEntrées avec nom vide mais autre données: {len(empty_name)}")
for r in empty_name[:5]:
    print(f"  Wilaya: {r.get('wilaya', '')}, Tel: {r.get('telephone', '')}, GPS: {r.get('latitude', '')}, URL: {r.get('google_maps_url', '')[:60]}")
