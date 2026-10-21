#!/usr/bin/env python3
"""Trouve les entrées sans GPS dans le checkpoint."""
import csv

checkpoint_path = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'

with open(checkpoint_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        lat = row.get('latitude', '').strip()
        lon = row.get('longitude', '').strip()
        if not lat or not lon:
            print(f"Ligne {i+2}:")
            print(f"  Raw row: {row}")
            print()

print("Recherche terminée")
