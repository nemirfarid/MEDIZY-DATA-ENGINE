"""
Phase 6 — tibdz.com enrichment: cross-reference + targeted scraping

Uses already-collected tibdz_all_entries.csv (976 entries from listing pages).
Cross-references with DB entries missing phones.
Scrapes only matched individual pages.
"""
import urllib.request
import json
import re
import time
import sys
import csv
import sqlite3
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'SANTE_DZ_Project/1.0 (Research; contact@projectsantaldz.org)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,ar;q=0.8,en;q=0.7',
}


def fetch_page(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            print(f'  Attempt {attempt+1} failed: {e}')
            time.sleep(1)
    return None


def scrape_individual_page(url):
    """Scrape individual doctor/facility page for phone and website."""
    html = fetch_page(url)
    if not html:
        return None, None

    tel = None
    site = None

    # Check JSON-LD
    pattern = r'<script type="application/ld\+json">(.*?)</script>'
    for m in re.finditer(pattern, html, re.DOTALL):
        try:
            data = json.loads(m.group(1).strip())
            if '@type' in data and data['@type'] in ('Physician', 'LocalBusiness', 'MedicalBusiness'):
                tel = tel or data.get('telephone')
                if not site:
                    sa = data.get('sameAs', [])
                    if isinstance(sa, str):
                        site = sa
                    elif isinstance(sa, list):
                        site = sa[0] if sa else None
                    if not site:
                        site = data.get('url')
        except json.JSONDecodeError:
            continue

    # Fallback: regex phone
    if not tel:
        phone_match = re.search(r'(0\d{8,9})', html)
        if phone_match:
            tel = phone_match.group(1)

    # Fallback: find external website
    if not site:
        url_matches = re.findall(r'href=["\'](https?://(?!tibdz\.com)[^"\']+)["\']', html)
        for u in url_matches:
            if 'facebook' not in u and 'google' not in u and 'linkedin' not in u:
                site = u
                break

    return tel, site


def normalize_name(name):
    """Normalize a name for fuzzy matching."""
    n = name.lower().strip()
    n = unicodedata.normalize('NFD', n)
    n = ''.join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r'[^\w\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def main():
    print('=== Phase 6 : tibdz.com enrichment ===')

    # Step 1: Load all tibdz entries
    tibdz_entries = []
    with open(r'D:\SANTE_DZ_EXPORTS\tibdz_all_entries.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tibdz_entries.append(row)
    print(f'Step 1: Loaded {len(tibdz_entries)} tibdz entries')

    # Build tibdz name -> data lookup
    tibdz_lookup = {}
    for entry in tibdz_entries:
        name_norm = normalize_name(entry['name'])
        tibdz_lookup[name_norm] = {
            'name': entry['name'],
            'url': entry['url'],
            'name_normalized': name_norm,
        }

    # Step 2: Cross-reference with DB
    print('Step 2: Cross-referencing with DB...')
    conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
    c = conn.cursor()

    c.execute('''
        SELECT id, nom, categorie_recherche, wilaya
        FROM places
        WHERE (telephone IS NULL OR telephone = '')
        AND categorie_recherche IN (?, ?, ?)
    ''', ('hôpital', 'clinique', 'centre de santé'))

    db_entries = c.fetchall()
    print(f'  DB entries without phone (hospital/clinique/centre): {len(db_entries)}')

    matched = []
    for db_id, db_name, cat, wilaya in db_entries:
        db_norm = normalize_name(db_name)
        db_words = set(db_norm.split())
        if len(db_words) < 2:
            continue

        best_match = None
        best_overlap = 0

        for tp_norm, tp_data in tibdz_lookup.items():
            tp_words = set(tp_norm.split())
            overlap = len(db_words & tp_words)
            if overlap >= 2 and overlap > best_overlap:
                best_overlap = overlap
                best_match = tp_data

        if best_match:
            matched.append({
                'db_id': db_id,
                'db_name': db_name,
                'db_category': cat,
                'db_wilaya': wilaya,
                'tibdz_name': best_match['name'],
                'tibdz_url': best_match['url'],
            })

    print(f'  Matched entries: {len(matched)}')

    # Step 3: Scrape individual pages for matched entries (with limit)
    print('Step 3: Scraping individual pages for matches...')
    enriched = []
    total_matched = len(matched)
    for i, m in enumerate(matched):
        progress = (i + 1) / total_matched * 100
        print(f'  [{i+1}/{total_matched}] ({progress:.0f}%) {m["db_name"]} -> {m["tibdz_name"]}')
        tel, site = scrape_individual_page(m['tibdz_url'])
        if tel or site:
            enriched.append({
                'db_id': m['db_id'],
                'db_name': m['db_name'],
                'tibdz_name': m['tibdz_name'],
                'tibdz_url': m['tibdz_url'],
                'phone': tel or '',
                'website': site or '',
            })
            print(f'    Found: tel={tel}, site={site}')
        time.sleep(1.0)  # Reduced rate limit

    # Save enriched
    with open(r'D:\SANTE_DZ_EXPORTS\tibdz_enriched.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['db_id', 'db_name', 'tibdz_name', 'tibdz_url', 'phone', 'website'])
        writer.writeheader()
        writer.writerows(enriched)
    print(f'\n  Enriched entries saved: {len(enriched)}')

    # Step 4: Update DB
    print('Step 4: Updating DB...')
    update_count = 0
    for e in enriched:
        updates = []
        params = []
        if e['phone']:
            updates.append('telephone = ?')
            params.append(e['phone'])
        if e['website']:
            updates.append('site_web = ?')
            params.append(e['website'])
        if updates:
            params.append(e['db_id'])
            c.execute(f'UPDATE places SET {", ".join(updates)} WHERE id = ?', params)
            conn.commit()
            update_count += 1

    conn.close()
    print(f'\n=== Terminé ===')
    print(f'  Total matched: {len(matched)}')
    print(f'  Enriched with phone/site: {len(enriched)}')
    print(f'  DB rows updated: {update_count}')


if __name__ == '__main__':
    main()
