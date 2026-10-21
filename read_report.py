with open(r'C:\SANTE_DZ_SCRAPER\phase6_5_1_reconciliation_report.txt', 'r', encoding='utf-8') as f:
    content = f.read()

def safe(s):
    return s.encode('ascii', 'replace').decode()

print(safe(content[:4000]))
print('\n...')
print('Total length:', len(content))