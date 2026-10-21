"""Inspect tibdz.com page structure."""
import urllib.request
import sys
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

url = 'https://tibdz.com/specialite/cliniques-et-hopitaux'
req = urllib.request.Request(url, headers=HEADERS)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    print(f'HTML length: {len(html)} chars')

    # Look for key patterns
    import re
    
    # Check for phone numbers
    phones = re.findall(r'0\d{8,9}', html[:10000])
    print(f'Phone patterns found in first 10k chars: {phones[:10]}')

    # Check for common div classes
    for pattern in ['result-item', 'fiche', 'card', 'entry', 'listing', 'post', 
                     'clinic', 'hopital', 'etablissement', 'annonce']:
        matches = re.findall(f'class="[^"]*{pattern}[^"]*"', html[:20000], re.IGNORECASE)
        if matches:
            print(f'Found class with "{pattern}": {matches[:5]}')

    # Check for pagination
    page_matches = re.findall(r'page=(\d+|page/\d+)', html[:20000])
    print(f'Pagination links: {page_matches[:10]}')

    # Print a snippet of the HTML to understand structure
    with open(r'C:\SANTE_DZ_SCRAPER\etablissements_sante_2025.txt', 'r', encoding='utf-8') as f:
        pass  # just checking file exists

    # Save HTML sample for inspection
    with open(r'C:\SANTE_DZ_SCRAPER\tibdz_sample.html', 'w', encoding='utf-8') as f:
        f.write(html[:20000])
    print('Saved HTML sample to tibdz_sample.html')

    # Check for phone pattern in raw content
    téléphone_matches = re.findall(r'Téléphone.*?(\d+)', html[:5000], re.IGNORECASE)
    print(f'Téléphone patterns: {téléphone_matches[:10]}')

    tel_matches = re.findall(r'tel.*?:.*?(\d+)', html[:5000], re.IGNORECASE)
    print(f'tel: patterns: {tel_matches[:10]}')

except Exception as e:
    print(f'Error: {e}')
