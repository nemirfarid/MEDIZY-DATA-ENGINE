"""Improved cross-reference: better fuzzy matching with Jaccard similarity."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import csv, sqlite3, unicodedata, re

def normalize_name(name):
    n = name.lower().strip()
    n = unicodedata.normalize('NFD', n)
    n = ''.join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r'[^\w\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def jaccard(a, b):
    a_words = set(a.split())
    b_words = set(b.split())
    if not a_words or not b_words:
        return 0
    intersection = len(a_words & b_words)
    union = len(a_words | b_words)
    return intersection / union

# Load tibdz entries
tibdz_entries = []
with open(r'D:\SANTE_DZ_EXPORTS\tibdz_all_entries.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        tibdz_entries.append(row)
print(f'tibdz entries: {len(tibdz_entries)}')

# Build lookup with normalized names
tibdz_lookup = []
for entry in tibdz_entries:
    name_norm = normalize_name(entry['name'])
    tibdz_lookup.append({
        'name': entry['name'],
        'url': entry['url'],
        'norm': name_norm,
    })

# DB entries without phone
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()
c.execute('''
    SELECT id, nom, categorie_recherche, wilaya
    FROM places
    WHERE (telephone IS NULL OR telephone = '')
    AND categorie_recherche IN (?, ?, ?)
''', ('hôpital', 'clinique', 'centre de santé'))

db_entries = c.fetchall()
print(f'DB entries without phone: {len(db_entries)}')

matched = []
used_tibdz = set()
for db_id, db_name, cat, wilaya in db_entries:
    db_norm = normalize_name(db_name)
    
    best_match = None
    best_score = 0
    
    for i, tp in enumerate(tibdz_lookup):
        if i in used_tibdz:
            continue
        score = jaccard(db_norm, tp['norm'])
        if score > 0.4 and score > best_score:  # At least 40% Jaccard similarity
            best_score = score
            best_match = (i, tp)
    
    if best_match:
        idx, tp = best_match
        used_tibdz.add(idx)
        matched.append({
            'db_id': db_id,
            'db_name': db_name,
            'db_category': cat,
            'db_wilaya': wilaya,
            'tibdz_name': tp['name'],
            'tibdz_url': tp['url'],
            'match_score': round(best_score, 3),
        })

print(f'Matched entries (Jaccard > 0.4): {len(matched)}')

# Save matched
with open(r'D:\SANTE_DZ_EXPORTS\tibdz_matched.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['db_id', 'db_name', 'db_category', 'db_wilaya', 'tibdz_name', 'tibdz_url', 'match_score'])
    writer.writeheader()
    writer.writerows(matched)

# Show first 20 matches
print('\nFirst 20 matches:')
for m in sorted(matched, key=lambda x: x['match_score'], reverse=True)[:20]:
    print(f'  [{m["match_score"]}] {m["db_name"][:45]} -> {m["tibdz_name"][:45]}')

conn.close()
