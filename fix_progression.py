#!/usr/bin/env python3
"""Fix progression.json v2 after recovery."""
import json
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

prog2_path = r'D:\SANTE_DZ_EXPORTS\scraping_progress.json'

# Read with utf-8-sig to handle BOM
with open(prog2_path, 'r', encoding='utf-8-sig') as f:
    prog2 = json.load(f)

# Update values from DB
prog2['total_national_unique'] = 23480
prog2['total_wilayas'] = 58
# Add Khenchela to terminees if not present
if 'Khenchela' not in prog2.get('wilayas_terminees', []):
    prog2['wilayas_terminees'] = prog2.get('wilayas_terminees', []) + ['Khenchela']
prog2['wilayas_erreur'] = []
prog2['wilaya_en_cours'] = None
prog2['last_request'] = ''
prog2['status'] = 'TERMINÉ'
prog2['timestamp'] = datetime.now().isoformat(timespec='seconds')

# Write without BOM
with open(prog2_path, 'w', encoding='utf-8') as f:
    json.dump(prog2, f, indent=2, ensure_ascii=False)

print(f'Progression v2 mise à jour')
wt = prog2.get('wilayas_terminees', [])
we = prog2.get('wilayas_erreur', [])
print(f'  wilayas_terminees: {len(wt)}')
print(f'  wilayas_erreur: {len(we)}')
print(f'  status: {prog2["status"]}')
print(f'  total_national_unique: {prog2["total_national_unique"]}')
