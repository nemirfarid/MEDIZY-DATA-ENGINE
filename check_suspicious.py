#!/usr/bin/env python3
"""Check for suspicious entries in checkpoint."""
import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f'Total rows in checkpoint: {len(rows)}')

# Find suspicious entries
suspicious_keywords = ['impossible', 'erreur', 'connexion', 'aucun résultat', 'non disponible', 'captcha']
suspicious = []
for r in rows:
    nom = (r.get('nom') or '').lower()
    adr = (r.get('adresse') or '').lower()
    for kw in suspicious_keywords:
        if kw in nom or kw in adr:
            suspicious.append(r)
            break

print(f'Suspicious entries: {len(suspicious)}')
for r in suspicious:
    print(f'  Nom: {r.get("nom", "")}')
    print(f'  Wilaya: {r.get("wilaya", "")}')
    print(f'  Cat: {r.get("categorie_recherche", "")}')
    print(f'  Adresse: {r.get("adresse", "")}')
    print(f'  Source: {r.get("source", "")}')
    print()

# Check the specific entry
print('=== Entry with "Impossible" ===')
for r in rows:
    if 'impossible' in (r.get('nom') or '').lower():
        for k in r:
            print(f'  {k}: {r[k]}')
        print()
