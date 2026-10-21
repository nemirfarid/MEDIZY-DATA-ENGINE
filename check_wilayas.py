#!/usr/bin/env Python3
"""Quick check of WILAYAS structure."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from communes_algerie import WILAYAS
from communes_officielles import get_all_communes

print(f"Type of WILAYAS: {type(WILAYAS)}")
print(f"Length: {len(WILAYAS)}")
if isinstance(WILAYAS, list):
    print(f"First item type: {type(WILAYAS[0])}")
    if isinstance(WILAYAS[0], dict):
        print(f"Keys: {list(WILAYAS[0].keys())}")
        for k, v in WILAYAS[0].items():
            print(f"  {k}: {v}")
elif isinstance(WILAYAS, dict):
    print(f"Keys sample: {list(WILAYAS.keys())[:3]}")

# Check communes_officielles structure
all_communes = get_all_communes()
print(f"\nCommunes total: {len(all_communes)}")
print(f"First commune:")
for k, v in all_communes[0].items():
    print(f"  {k}: {v}")
