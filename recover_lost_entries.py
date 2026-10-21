#!/usr/bin/env python3
"""
Phase 4.1 - Recovery and deduplication script.

Sources compared:
  1. checkpoint.csv (current baseline)
  2. checkpoint_enrichment.csv
  3. checkpoint_20260926_014602.csv (snapshot)
  4. backups/medizy_scraper_backup_20261010_014940.db (old DB, 16 wilayas from September)

Recovery strategy:
  - New unique entries: URL not in checkpoint AND place_id not in checkpoint
  - Field enrichment: for conflicts (same place_id, different URL), fill missing
    fields from historical versions where data is more complete
  - Conflict reporting: entries with significant differences are reported, not auto-merged
  - Provenance tracking: each recovered entry is tagged with its source

Usage:
  python recover_lost_entries.py                    # simulation mode (no changes)
  python recover_lost_entries.py --apply            # apply recovery to checkpoint
  python recover_lost_entries.py --report           # generate detailed report only
"""
import csv, sqlite3, sys, os, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, OrderedDict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# === CONFIGURATION ===
CHECKPOINT_PATH = r'D:\SANTE_DZ_EXPORTS\checkpoint.csv'
ENRICHMENT_PATH = r'D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv'
SNAPSHOT_PATH = r'D:\SANTE_DZ_EXPORTS\snapshots\checkpoint_20260926_014602.csv'
OLD_DB_PATH = r'C:\SANTE_DZ_SCRAPER\backups\medizy_scraper_backup_20261010_014940.db'
FIELDS = ['wilaya', 'commune', 'categorie_recherche', 'nom', 'adresse', 'telephone', 'site_web',
          'note', 'nombre_avis', 'horaires', 'latitude', 'longitude', 'google_maps_url',
          'place_id_si_visible', 'type_google', 'statut', 'scrape_date', 'source']

# Fields where historical data can enrich the checkpoint (if non-empty and checkpoint is empty)
ENRICHABLE_FIELDS = ['telephone', 'site_web', 'note', 'nombre_avis', 'horaires', 'latitude', 'longitude',
                     'type_google', 'adresse']

# Fields that should NOT be taken from historical sources (placeholder/unreliable)
UNRELIABLE_VALUES = {
    'adresse': ['itinéraires'],  # Google Maps default text for "Directions"
    'nom': [''],  # Empty names are useless
}

def clean(s):
    if s is None:
        return ''
    return str(s).strip()

def count_filled(row):
    """Count non-empty fields in a row."""
    return sum(1 for v in row.values() if v and str(v).strip())

def is_reliable(field, value):
    """Check if a value is reliable (not placeholder/unreliable)."""
    v = str(value).strip().lower()
    if field in UNRELIABLE_VALUES:
        if v in UNRELIABLE_VALUES[field]:
            return False
    return v != ''

def load_csv_source(path, source_name):
    """Load a CSV file."""
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows

def load_db_source(db_path):
    """Load entries from SQLite DB places table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Handle both 'statut' and 'status' columns in old DB
    cursor.execute("PRAGMA table_info(places)")
    cols = [r[1] for r in cursor.fetchall()]
    status_col = 'status' if 'status' in cols and 'statut' not in cols else 'statut'
    
    cursor.execute(f"""
        SELECT wilaya, commune, categorie_recherche, nom, adresse, telephone, site_web,
               note, nombre_avis, horaires, CAST(latitude AS TEXT), CAST(longitude AS TEXT),
               google_maps_url, place_id, type_google, {status_col}, scrape_date, source
        FROM places
    """)
    rows = []
    for r in cursor.fetchall():
        row = dict(zip(FIELDS, r))
        for k in row:
            if row[k] is None:
                row[k] = ''
        rows.append(row)
    conn.close()
    return rows

def build_index(rows):
    """Build URL and place_id indexes from a list of rows."""
    by_url = {}
    by_pid = {}
    all_urls = set()
    all_pids = set()
    for r in rows:
        url = r.get('google_maps_url', '').strip()
        pid = r.get('place_id_si_visible', '').strip()
        if url:
            by_url[url] = r
            all_urls.add(url)
        if pid:
            by_pid[pid] = r
            all_pids.add(pid)
    return by_url, by_pid, all_urls, all_pids

def analyze_recovery():
    """Analyze all sources and determine recovery actions."""

    print("=" * 70)
    print("PHASE 4.1 — RÉCUPÉRATION DES FICHES HISTORIQUES")
    print("=" * 70)

    # === Load all sources ===
    print("\n[1] Chargement du checkpoint actuel...")
    ckpt_rows = load_csv_source(CHECKPOINT_PATH, "checkpoint")

    print("\n[2] Chargement des sources historiques...")
    enr_rows = load_csv_source(ENRICHMENT_PATH, "enrichment")
    snap_rows = load_csv_source(SNAPSHOT_PATH, "snapshot")
    old_db_rows = load_db_source(OLD_DB_PATH)

    print(f"    checkpoint.csv: {len(ckpt_rows)} rows")
    print(f"    checkpoint_enrichment.csv: {len(enr_rows)} rows")
    print(f"    checkpoint_20260926_014602.csv: {len(snap_rows)} rows")
    print(f"    old_DB_backup: {len(old_db_rows)} rows")

    # Build indexes
    ckpt_by_url, ckpt_by_pid, ckpt_urls, ckpt_pids = build_index(ckpt_rows)
    enr_by_url, enr_by_pid, enr_urls, enr_pids = build_index(enr_rows)
    snap_by_url, snap_by_pid, snap_urls, snap_pids = build_index(snap_rows)
    old_by_url, old_by_pid, old_urls, old_pids = build_index(old_db_rows)

    # All historical URLs and PIDs (union)
    hist_by_url = {}
    hist_by_pid = {}
    hist_all_urls = set()
    hist_all_pids = set()

    # Merge historical sources, keeping most complete row for each URL/PID
    for source_rows, source_name in [(enr_rows, 'enrichment'), (snap_rows, 'snapshot'), (old_db_rows, 'old_db')]:
        for r in source_rows:
            r['_recovery_source'] = source_name
            url = r.get('google_maps_url', '').strip()
            pid = r.get('place_id_si_visible', '').strip()
            if url:
                if url not in hist_all_urls:
                    hist_all_urls.add(url)
                    hist_by_url[url] = r
                else:
                    if count_filled(r) > count_filled(hist_by_url[url]):
                        hist_by_url[url] = r
            if pid:
                if pid not in hist_all_pids:
                    hist_all_pids.add(pid)
                    hist_by_pid[pid] = r
                else:
                    if count_filled(r) > count_filled(hist_by_pid[pid]):
                        hist_by_pid[pid] = r

    print(f"\n    URLs historiques uniques: {len(hist_all_urls)}")
    print(f"    place_ids historiques uniques: {len(hist_all_pids)}")

    # === Analysis ===
    print("\n[3] Analyse comparative...")

    # Categorize entries
    new_unique = []  # truly new entries (URL + PID not in checkpoint)
    field_enrichments = []  # existing entries that can be enriched
    conflicts = []  # same PID, different URL, data differences need review
    duplicate_urls = []  # exact URL match in checkpoint

    for url, hist_row in hist_by_url.items():
        pid = hist_row.get('place_id_si_visible', '').strip()

        # Case 1: URL is already in checkpoint
        if url in ckpt_urls:
            duplicate_urls.append({
                'source': hist_row.get('_recovery_source', '?'),
                'url': url,
                'pid': pid,
                'type': 'duplicate_exact_url'
            })
            continue

        # Case 2: URL is new, but PID exists in checkpoint (conflict)
        if pid and pid in ckpt_by_pid:
            ckpt_row = ckpt_by_pid[pid]
            # Check if data is different
            field_diffs = {}
            for field in ENRICHABLE_FIELDS:
                cv = clean(ckpt_row.get(field, ''))
                hv = clean(hist_row.get(field, ''))
                if cv != hv:
                    field_diffs[field] = {'ckpt': cv, 'hist': hv}

            if field_diffs:
                conflicts.append({
                    'source': hist_row.get('_recovery_source', '?'),
                    'pid': pid,
                    'ckpt_url': ckpt_row.get('google_maps_url', '').strip(),
                    'hist_url': url,
                    'diffs': field_diffs,
                    'hist_row': hist_row,
                    'ckpt_row': ckpt_row,
                })
            else:
                # Same data, just different URL - no conflict needed
                conflicts.append({
                    'source': hist_row.get('_recovery_source', '?'),
                    'pid': pid,
                    'ckpt_url': ckpt_row.get('google_maps_url', '').strip(),
                    'hist_url': url,
                    'diffs': {},
                    'hist_row': hist_row,
                    'ckpt_row': ckpt_row,
                })
            continue

        # Case 3: URL is new AND PID is new or empty - truly new entry
        if pid and pid in ckpt_pids:
            # URL is new but PID is in checkpoint (shouldn't happen, caught above)
            continue
        new_unique.append({
            'source': hist_row.get('_recovery_source', '?'),
            'row': hist_row,
        })

    # Also check historical entries with empty URL but with PID
    for pid, hist_row in hist_by_pid.items():
        if pid in ckpt_pids:
            # Same PID in checkpoint - already handled via conflict
            pass
        else:
            url = hist_row.get('google_maps_url', '').strip()
            if not url:
                # No URL, no conflict -> new entry
                existing = [e for e in new_unique if e['row'].get('place_id_si_visible', '').strip() == pid]
                if not existing:
                    new_unique.append({
                        'source': hist_row.get('_recovery_source', '?'),
                        'row': hist_row,
                        'note': 'no_url'
                    })

    # Deduplicate new_unique by PID and URL
    seen_pids = set()
    seen_urls = set()
    final_new_unique = []
    for entry in new_unique:
        r = entry['row']
        pid = r.get('place_id_si_visible', '').strip()
        url = r.get('google_maps_url', '').strip()
        key = f"{pid}_{url}"
        if key in seen_pids or (pid and pid in seen_pids) or (url and url in seen_urls):
            continue
        if pid:
            seen_pids.add(pid)
        if url:
            seen_urls.add(url)
        final_new_unique.append(entry)

    # Deduplicate conflicts by PID
    seen_conflict_pids = set()
    final_conflicts = []
    for c in conflicts:
        if c['pid'] in seen_conflict_pids:
            continue
        seen_conflict_pids.add(c['pid'])
        final_conflicts.append(c)

    # === Detailed conflict analysis ===
    print("\n[4] Analyse détaillée des conflits...")

    # Field enrichment opportunities
    enrichment_fields = defaultdict(lambda: defaultdict(int))  # field -> source -> count

    more_complete = []
    equal = []
    less_complete = []

    for c in final_conflicts:
        hist_score = count_filled(c['hist_row'])
        ckpt_score = count_filled(c['ckpt_row'])
        if hist_score > ckpt_score:
            more_complete.append(c)
        elif hist_score == ckpt_score:
            equal.append(c)
        else:
            less_complete.append(c)

        # Check which fields can be enriched
        for field in ENRICHABLE_FIELDS:
            cv = clean(c['ckpt_row'].get(field, ''))
            hv = clean(c['hist_row'].get(field, ''))
            if hv and not cv and is_reliable(field, hv):
                enrichment_fields[field][c['source']] += 1

    print(f"    Total conflits: {len(final_conflicts)}")
    print(f"    Plus complète (hist > ckpt): {len(more_complete)}")
    print(f"    Égale: {len(equal)}")
    print(f"    Moins complète: {len(less_complete)}")

    print("\n    Opportunities d'enrichissement de champs:")
    for field, sources in enrichment_fields.items():
        total = sum(sources.values())
        print(f"      {field}: {total} champs à enrichir (sources: {dict(sources)})")

    # === Summary ===
    print("\n" + "=" * 70)
    print("RÉSUMÉ DE LA RÉCUPÉRATION")
    print("=" * 70)

    report = {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'checkpoint': {
            'total_rows': len(ckpt_rows),
            'distinct_urls': len(ckpt_urls),
            'distinct_pids': len(ckpt_pids),
        },
        'historical_sources': {
            'checkpoint_enrichment': {'rows': len(enr_rows), 'urls': len(enr_urls), 'pids': len(enr_pids)},
            'checkpoint_snapshot': {'rows': len(snap_rows), 'urls': len(snap_urls), 'pids': len(snap_pids)},
            'old_db_backup': {'rows': len(old_db_rows), 'urls': len(old_urls), 'pids': len(old_pids)},
        },
        'recovery': {
            'new_unique_entries': len(final_new_unique),
            'entries_without_url': sum(1 for e in final_new_unique if not e['row'].get('google_maps_url', '').strip()),
            'entries_with_url': sum(1 for e in final_new_unique if e['row'].get('google_maps_url', '').strip()),
            'duplicate_urls': len(duplicate_urls),
            'conflicts_same_pid_diff_url': len(final_conflicts),
            'field_enrichment_opportunities': {k: sum(v.values()) for k, v in enrichment_fields.items()},
        },
        'conflicts_breakdown': {
            'more_complete': len(more_complete),
            'equal': len(equal),
            'less_complete': len(less_complete),
        },
        'projected_total': {
            'checkpoint_unique_urls': len(ckpt_urls),
            'new_unique_url_entries': sum(1 for e in final_new_unique if e['row'].get('google_maps_url', '').strip()),
            'field_enriched_entries': len(more_complete),
            'projected_db_total': len(ckpt_pids) + sum(1 for e in final_new_unique if e['row'].get('place_id_si_visible', '').strip()),
        },
    }

    print(f"\n  Entrées récupérables (nouvelles, URL non vide): {report['recovery']['entries_with_url']}")
    print(f"  Entrées récupérables (sans URL, identifiables par place_id): {report['recovery']['entries_without_url']}")
    print(f"  Doublons certains (URL identique): {report['recovery']['duplicate_urls']}")
    print(f"  Conflits (place_id existant, URL différente): {report['recovery']['conflicts_same_pid_diff_url']}")
    print(f"  Opportunités d'enrichissement: {sum(report['recovery']['field_enrichment_opportunities'].values())} champs")

    print(f"\n  Après récupération:")
    print(f"    Nouvelles entrées uniques: {report['recovery']['new_unique_entries']}")
    print(f"    Entrées enrichies (champs complémentaires): {len(more_complete)}")
    print(f"    Total projeté dans DB: {report['projected_total']['projected_db_total']}")

    # Wilaya breakdown of new entries
    print("\n  Nouvelles entrées par wilaya:")
    new_by_wilaya = defaultdict(int)
    for entry in final_new_unique:
        w = entry['row'].get('wilaya', '').strip()
        if w:
            new_by_wilaya[w] += 1
    for w, c in sorted(new_by_wilaya.items()):
        print(f"    {w}: {c}")

    # Category breakdown of new entries
    print("\n  Nouvelles entrées par catégorie:")
    new_by_cat = defaultdict(int)
    for entry in final_new_unique:
        c = entry['row'].get('categorie_recherche', '').strip()
        if c:
            new_by_cat[c] += 1
    for c, cnt in sorted(new_by_cat.items()):
        print(f"    {c}: {cnt}")

    # Field enrichment details
    print("\n  Détails des enrichissements possibles:")
    for field, sources in enrichment_fields.items():
        total = sum(sources.values())
        print(f"    {field}: {total} entrées ({dict(sources)})")

    return report, final_new_unique, more_complete, conflicts

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Recover lost historical entries')
    parser.add_argument('--apply', action='store_true', help='Apply recovery to checkpoint')
    parser.add_argument('--report', action='store_true', help='Generate detailed report only')
    args = parser.parse_args()

    report, new_unique, more_complete, conflicts = analyze_recovery()

    if not args.apply and not args.report:
        print("\n" + "=" * 70)
        print("MODE SIMULATION — Aucune modification n'a été effectuée.")
        print(f"Pour appliquer: python recover_lost_entries.py --apply")
        print("=" * 70)
    elif args.report:
        print("\n  Mode rapport uniquement.")
