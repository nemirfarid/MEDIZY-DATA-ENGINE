# -*- coding: utf-8 -*-
import json, csv, hashlib
from pathlib import Path

prog_path = Path(r'D:\SANTE_DZ_EXPORTS\progression.json')
ckpt_path = Path(r'D:\SANTE_DZ_EXPORTS\checkpoint.csv')

# Progression
data = json.loads(prog_path.read_text(encoding='utf-8'))
completed = data.get('completed', [])
current = data.get('current')
print('=== PROGRESSION ===')
print('completed count:', len(completed))
print('current:', current)
print('updated_at:', data.get('updated_at'))

# Wilayas terminees
wilayas_done = set(w for w, c in completed if isinstance(w, str))
print('wilayas done:', len(wilayas_done))
for w in sorted(wilayas_done):
    cats = [c for ww, c in completed if ww == w]
    print('  {}: {}/34'.format(w, len(cats)))

# Checkpoint
with ckpt_path.open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
print()
print('=== CHECKPOINT ===')
print('total rows:', len(rows))

# Wilayas dans checkpoint
wilayas_ckpt = {}
for r in rows:
    w = r.get('wilaya', '').strip()
    if w:
        wilayas_ckpt.setdefault(w, 0)
        wilayas_ckpt[w] += 1
print('wilayas in checkpoint:', len(wilayas_ckpt))
for w in sorted(wilayas_ckpt.keys()):
    print('  {}: {}'.format(w, wilayas_ckpt[w]))

# Doublons par stable_key
def stable_key(row):
    raw = '|'.join([
        (row.get('nom', '') or '').strip().lower(),
        (row.get('adresse', '') or '').strip().lower(),
        (row.get('telephone', '') or '').strip(),
        str(row.get('latitude') or ''),
        str(row.get('longitude') or ''),
    ])
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()

keys = [stable_key(r) for r in rows]
unique = len(set(keys))
print('unique by stable_key:', unique)
print('duplicates:', len(rows) - unique)

# GPS, Phone, Place ID
gps = sum(1 for r in rows if r.get('latitude') and r['latitude'].strip() and r.get('longitude') and r['longitude'].strip())
phone = sum(1 for r in rows if r.get('telephone') and r['telephone'].strip())
pid = sum(1 for r in rows if r.get('place_id_si_visible') and r['place_id_si_visible'].strip())
address = sum(1 for r in rows if r.get('adresse') and r['adresse'].strip())
website = sum(1 for r in rows if r.get('site_web') and r['site_web'].strip())
print('GPS: {} ({:.1f}%)'.format(gps, gps/len(rows)*100))
print('Phone: {} ({:.1f}%)'.format(phone, phone/len(rows)*100))
print('Place ID: {} ({:.1f}%)'.format(pid, pid/len(rows)*100))
print('Address: {} ({:.1f}%)'.format(address, address/len(rows)*100))
print('Website: {} ({:.1f}%)'.format(website, website/len(rows)*100))

# Derniere fiche
last = rows[-1] if rows else {}
print()
print('=== DERNIERE FICHE ===')
print('nom: {}'.format(last.get('nom', '')[:80]))
print('wilaya: {}'.format(last.get('wilaya', '')))
print('category: {}'.format(last.get('categorie_recherche', '')))
print('scrape_date: {}'.format(last.get('scrape_date', '')))