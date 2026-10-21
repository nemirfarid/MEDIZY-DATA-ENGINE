"""
Scrape individual tibdz.com pages for matched entries to get phone + website.
Reads from tibdz_matched.csv and updates DB.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import json
import re
import time
import csv
import sqlite3

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
            print(f'    Attempt {attempt+1} failed: {e}')
            time.sleep(1)
    return None


def scrape_individual_page(url):
    """Extract phone and website from an individual tibdz.com doctor page."""
    html = fetch_page(url)
    if not html:
        return None, None

    tel = None
    site = None

    # JSON-LD schema
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

    # Fallback: regex phone (Algerian format: 0 + 9 digits typically)
    if not tel:
        phone_match = re.search(r'(0\d{9})', html)
        if phone_match:
            tel = phone_match.group(1)

    # Fallback: external website
    if not site:
        url_matches = re.findall(r'href=["\'](https?://(?!tibdz\.com)[^"\']+)["\']', html)
        for u in url_matches:
            if 'facebook' not in u and 'google' not in u and 'linkedin' not in u:
                site = u
                break

    return tel, site


def main():
    print('=== Phase 6 : tibdz.com individual page scraping ===')

    # Load matched entries
    matched = []
    with open(r'D:\SANTE_DZ_EXPORTS\tibdz_matched.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            matched.append(row)
    print(f'Matched entries to scrape: {len(matched)}')

    conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
    c = conn.cursor()

    enriched = []
    for i, m in enumerate(matched):
        db_id = int(m['db_id'])
        db_name = m['db_name']
        tibdz_name = m['tibdz_name']
        tibdz_url = m['tibdz_url']
        score = m['match_score']

        print(f'  [{i+1}/{len(matched)}] [{score}] {db_name[:40]} -> {tibdz_name[:40]}')

        tel, site = scrape_individual_page(tibdz_url)
        if tel or site:
            enriched.append({
                'db_id': db_id,
                'db_name': db_name,
                'tibdz_name': tibdz_name,
                'phone': tel or '',
                'website': site or '',
            })
            print(f'    Found: tel={tel}, site={site}')
        else:
            print(f'    No phone/site found')

        time.sleep(1.0)  # Rate limit

    # Save results
    with open(r'D:\SANTE_DZ_EXPORTS\tibdz_enriched.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['db_id', 'db_name', 'tibdz_name', 'phone', 'website'])
        writer.writeheader()
        writer.writerows(enriched)
    print(f'\nEnriched entries: {len(enriched)}')

    # Update DB
    print('\nUpdating DB...')
    updated = 0
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
            updated += 1
    conn.close()

    print(f'\n=== Terminé ===')
    print(f'  Matched entries: {len(matched)}')
    print(f'  Enriched with phone/site: {len(enriched)}')
    print(f'  DB rows updated: {updated}')


if __name__ == '__main__':
    main()
