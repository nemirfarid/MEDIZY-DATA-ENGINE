#!/usr/bin/env python3
"""Find categories marked completed but with 0 entries in checkpoint."""
import csv, json, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load checkpoint
with open(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Count entries per (wilaya, category)
pair_counts = defaultdict(int)
for r in rows:
    w = r.get('wilaya', '').strip()
    c = r.get('categorie_recherche', '').strip()
    if w and c:
        pair_counts[(w, c)] += 1

# Load progression v1
with open(r'D:\SANTE_DZ_EXPORTS\progression.json', 'r', encoding='utf-8') as f:
    prog = json.load(f)

completed_pairs = prog.get('completed', [])
print(f"Total [wilaya, categorie] marqués comme terminés: {len(completed_pairs)}")

# Find pairs marked completed but with 0 entries
empty_pairs = []
for pair in completed_pairs:
    w = pair[0]
    c = pair[1]
    count = pair_counts.get((w, c), 0)
    if count == 0:
        empty_pairs.append((w, c))

print(f"Pairs terminés mais 0 entrées dans checkpoint: {len(empty_pairs)}")

# Group by wilaya
empty_by_wilaya = defaultdict(list)
for w, c in empty_pairs:
    empty_by_wilaya[w].append(c)

print(f"\nWilayas avec catégories vides:")
for w in sorted(empty_by_wilaya.keys()):
    cats = empty_by_wilaya[w]
    print(f"  {w}: {len(cats)} catégories vides -> {cats}")

# Also check: for each wilaya, which categories have 0 entries?
categories = ["médecin", "cabinet médical", "médecin généraliste", "médecin spécialiste",
              "dentiste", "cabinet dentaire", "pharmacie", "laboratoire médical",
              "clinique", "hôpital", "polyclinique", "centre médical", "centre de santé",
              "radiologue", "centre de radiologie", "kinésithérapeute", "kinésithérapie",
              "sage-femme", "ophtalmologue", "pédiatre", "gynécologue", "cardiologue",
              "dermatologue", "ORL", "neurologue", "urologue", "gastro-entérologue",
              "psychologue", "psychiatre", "nutritionniste", "orthophoniste", "ostéopathe",
              "vétérinaire", "centre d'imagerie médicale"]

all_wilayas = sorted(set(r['wilaya'].strip() for r in rows if r.get('wilaya', '').strip()))
print(f"\n=== COMPLETENESS BY WILAYA (categories with 0 entries) ===")
total_empty = 0
for w in all_wilayas:
    empty_cats = []
    for c in categories:
        count = pair_counts.get((w, c), 0)
        if count == 0:
            empty_cats.append(c)
    if empty_cats:
        print(f"  {w}: {len(empty_cats)}/{len(categories)} categories vides")
        total_empty += len(empty_cats)
    total_empty += 0

print(f"\nTotal (wilaya, category) pairs with 0 entries: {total_empty}")
print(f"Max possible if all complete: {len(all_wilayas) * len(categories)}")
