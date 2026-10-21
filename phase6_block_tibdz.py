"""
Phase 6.1 — Blocage de l'import tibdz invalide

Ce script analyse tibdz_enriched.csv et DÉMONTRE qu'il est inutilisable.
Il NE MODIFIE PAS la base de données.

Constat: 163 entrées, TOUTES avec téléphone=0104346352 et site=https://fonts.gstatic.com
"""

import csv
from collections import Counter

TIBDZ_ENRICHED = r'D:\SANTE_DZ_EXPORTS\tibdz_enriched.csv'
TIBDZ_ALL = r'D:\SANTE_DZ_EXPORTS\tibdz_all_entries.csv'

def analyze_tibdz_enriched():
    print('=' * 70)
    print('ANALYSE tibdz_enriched.csv — DÉTECTION DONNÉES INVALIDES')
    print('=' * 70)

    with open(TIBDZ_ENRICHED, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f'Total lignes: {len(rows)}')
    print(f'Colonnes: {reader.fieldnames}')

    # Compter téléphones uniques
    phones = [r['phone'] for r in rows]
    phone_counts = Counter(phones)
    print(f'\nTéléphones uniques: {len(phone_counts)}')
    for phone, count in phone_counts.most_common(5):
        print(f'  {phone}: {count} occurrences ({count/len(rows)*100:.1f}%)')

    # Compter sites uniques
    sites = [r['website'] for r in rows]
    site_counts = Counter(sites)
    print(f'\nSites uniques: {len(site_counts)}')
    for site, count in site_counts.most_common(5):
        print(f'  {site}: {count} occurrences ({count/len(rows)*100:.1f}%)')

    # Vérifier si TOUS identiques
    all_same_phone = len(phone_counts) == 1
    all_same_site = len(site_counts) == 1

    print(f'\nWARNING: TOUS téléphones identiques: {all_same_phone}')
    print(f'WARNING: TOUS sites identiques: {all_same_site}')

    if all_same_phone and all_same_site:
        print('\n' + '!' * 70)
        print('CONCLUSION: DONNEES CORROMPUES -- TEMPLATE/PLACEHOLDER DETECTE')
        print('  - Telephone unique: 0104346352 (probablement numero par defaut du site)')
        print('  - Site unique: https://fonts.gstatic.com (CDN Google Fonts, PAS site etablissement)')
        print('  - 163 etablissements differents -> MEMES coordonnees de contact')
        print('  - IMPOSSIBLE d\'importer sans creer 163 faux doublons de contact')
        print('!' * 70)

    return all_same_phone and all_same_site


def analyze_tibdz_all():
    print('\n' + '=' * 70)
    print('ANALYSE tibdz_all_entries.csv — SOURCE BRUTE (976 entrées)')
    print('=' * 70)

    with open(TIBDZ_ALL, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f'Total lignes: {len(rows)}')
    print(f'Colonnes: {reader.fieldnames}')

    # Échantillon
    print('\nPremières 5 entrées:')
    for r in rows[:5]:
        print(f"  {r['name']} -> {r['url']}")

    # Vérifier structure URLs
    urls = [r['url'] for r in rows]
    unique_urls = set(urls)
    print(f'\nURLs uniques: {len(unique_urls)} / {len(urls)}')
    if len(unique_urls) == len(urls):
        print('  ✅ Toutes URLs uniques (bon signe pour le scraping ciblé)')
    else:
        print(f'  ⚠️  {len(urls) - len(unique_urls)} URLs dupliquées')


def recommend_controls():
    print('\n' + '=' * 70)
    print('CONTRÔLES REQUIS POUR FUTUR SCRAPING TIBDZ')
    print('=' * 70)
    controls = [
        ('Phone diversity', 'Rejeter tout lot où >50% des telephones sont identiques'),
        ('Website diversity', 'Rejeter tout lot où >50% des sites sont identiques'),
        ('CDN/Template detection', 'Bloquer domaines: fonts.gstatic.com, googleapis.com, cdn.*, *.cloudflare.com'),
        ('Phone format', 'Valider format Algerie: ^0[5679]\\d{8}$'),
        ('Cross-ref verification', 'Exiger correspondance nom+wilaya avant scraping page detail'),
        ('Rate limit', 'Respecter 1 req/sec + backoff exponentiel sur 429/5xx'),
        ('Idempotence', 'Cle stable: tibdz_url UNIQUE + verif metier nom+wilaya'),
        ('Provenance', 'Conserver tibdz_url, date_scrape, raw_html_hash'),
    ]
    for name, desc in controls:
        print(f'  • {name}: {desc}')

    print('\n❌ RECOMMANDATION: NE PAS IMPORTER tibdz_enriched.csv')
    print('❌ RECOMMANDATION: NE PAS EXÉCUTER phase6_scrape_tibdz.py sur base active')
    print('✅ ACTION: Réécrire le scraper avec contrôles ci-dessus OU abandonner tibdz')


if __name__ == '__main__':
    corrupted = analyze_tibdz_enriched()
    analyze_tibdz_all()
    recommend_controls()

    print('\n' + '=' * 70)
    print('RESUME FINAL')
    print('=' * 70)
    if corrupted:
        print('STATUT: BLOQUE -- Donnees tibdz invalides detectees')
        print('Aucune modification de base de donnees effectuee.')
        exit(1)
    else:
        print('STATUT: OK -- Donnees exploitables (cas non rencontre)')
        exit(0)