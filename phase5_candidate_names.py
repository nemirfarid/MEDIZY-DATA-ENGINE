#!/usr/bin/env Python3
"""
Phase 5 — Étape 3: Examiner les 935 entrées CANDIDATE.
Tenter d'extraire les noms réels depuis les URLs Google Maps.
Format typique: https://www.google.com/maps/place/Nom+de+l'établissement/data=!...

NE MODIFIE AUCUNE DONNÉE — lecture seule + proposition.
"""
import csv, sys, urllib.parse, re
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CHECKPOINT = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'

# Read checkpoint and extract CANDIDATE entries
with open(CHECKPOINT, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    ckpt_rows = list(reader)

candidates = [r for r in ckpt_rows if r.get('name_status', 'VERIFIED') == 'CANDIDATE']
print(f"Total CANDIDATE entries: {len(candidates)}")

# Try to extract name from URL
# Google Maps URL format: https://www.google.com/maps/place/Nom+de+l'établissement/data=!...
# or https://www.google.com/maps/place/CID_... (for place IDs in URL)

name_from_url = 0
name_not_found = 0
samples = []

ERROR_PATTERNS = ['impossible', 'erreur', 'timeout', 'captcha', 'introuvable']

def extract_name_from_url(url):
    """Try to extract establishment name from Google Maps URL."""
    if not url or not url.startswith('http'):
        return None, None
    
    # Try /place/ pattern
    # Format: .../place/Nom+de+l'établissement/data=!...
    match = re.search(r'/place/([^/]+?)(?:/data=|/$)', url)
    if match:
        raw = match.group(1)
        # Decode URL encoding
        decoded = urllib.parse.unquote_plus(raw)
        # Check if it's a data= parameter (not a real name)
        if decoded.startswith('data=') or 'data=' in decoded:
            return None, 'data_param'
        # Check if it's a place ID (CID_...)
        if decoded.startswith('CID_') or decoded.startswith('ChIJ'):
            return None, 'place_id_in_url'
        # Check if it looks like an error message
        if any(p in decoded.lower() for p in ERROR_PATTERNS):
            return None, 'error_in_url'
        # Check if it's a reasonable name (at least 3 chars, not just numbers)
        if len(decoded) >= 3 and not decoded.replace(' ', '').isdigit():
            return decoded.strip(), 'ok'
        return None, 'too_short_or_numeric'
    
    # Try /search/ pattern
    match = re.search(r'/search/([^/?]+)', url)
    if match:
        decoded = urllib.parse.unquote_plus(match.group(1))
        if len(decoded) >= 3:
            return decoded.strip(), 'ok'
    
    return None, 'no_match'

extracted = []
for r in candidates:
    url = r.get('google_maps_url', '').strip()
    name, reason = extract_name_from_url(url)
    
    if name:
        # Double-check it's not an error message
        if not any(p in name.lower() for p in ERROR_PATTERNS):
            name_from_url += 1
            extracted.append({
                'nom_recupere': name,
                'nom_original': r.get('nom', ''),
                'wilaya': r.get('wilaya', ''),
                'categorie': r.get('categorie_recherche', ''),
                'telephone': r.get('telephone', ''),
                'note': r.get('note', ''),
                'gps': f"{r.get('latitude', '')}, {r.get('longitude', '')}",
                'url': url[:80],
                'extraction_reason': reason,
            })
            if len(samples) < 10:
                samples.append({
                    'nom_recupere': name[:60],
                    'nom_original': r.get('nom', '')[:60],
                    'wilaya': r.get('wilaya', ''),
                    'categorie': r.get('categorie_recherche', '')[:30],
                    'url': url[:80],
                })
        else:
            name_not_found += 1
    else:
        name_not_found += 1

print(f"\n=== RÉSULTATS DE L'EXTRACTION ===")
print(f"Names successfully extracted from URL: {name_from_url}")
print(f"Names not found in URL: {name_not_found}")

# Show samples
print(f"\n=== ÉCHANTILLON (10 extraits) ===")
for s in samples:
    print(f"  Nom récupéré: {s['nom_recupere'][:50]}")
    print(f"    Wilaya: {s['wilaya']}")
    print(f"    Catégorie: {s['categorie']}")
    print(f"    URL: {s['url']}")
    print()

# Analyze by wilaya
print(f"\n=== Extraction par wilaya (top 10) ===")
by_wilaya = Counter(e['wilaya'] for e in extracted)
for w, c in by_wilaya.most_common(10):
    print(f"  {w}: {c}")

# Analyze by category
print(f"\n=== Extraction par catégorie (top 10) ===")
by_cat = Counter(e['categorie'] for e in extracted)
for cat, c in by_cat.most_common(10):
    print(f"  {cat}: {c}")

# Check for potential duplicates among extracted names
print(f"\n=== Analyse de similarité ===")
nom_set = set()
duplicates = 0
for e in extracted:
    nom_lower = e['nom_recupere'].lower().strip()
    if nom_lower in nom_set:
        duplicates += 1
    nom_set.add(nom_lower)
print(f"Names uniques extraites: {len(nom_set)} / {len(extracted)}")
print(f"Noms en double: {duplicates}")

# Save extracted names to file for review
review_file = r'D:\SANTE_DZ_EXPORTS\candidate_names_extracted.csv'
with open(review_file, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(extracted[0].keys()) if extracted else ['nom_recupere'])
    writer.writeheader()
    writer.writerows(extracted)

print(f"\nRapport d'extraction sauvegardé: {review_file}")
print(f"\n=== CONCLUSION ===")
print(f"{name_from_url} noms récupérés depuis URLs sur {len(candidates)} candidats")
if name_from_url > 0:
    print(f"Ces entrées peuvent être réintégrées dans la DB après vérification")
    print(f"Les {name_not_found} restantes nécessitent une visite manuelle des URLs")
