#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Merge staging OSM entries into production (dry-run or real).
Usage: python merge_staging_to_prod.py --dry-run   (or --apply)
Read-only on production except during --apply (which writes inserts only).
"""
import sqlite3
import sys
import argparse
import hashlib

STAGING = r"C:\SANTE_DZ_SCRAPER\staging_osm_pilot.db"
PROD = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"

def sha256(p):
    import os
    if not os.path.exists(p):
        return "N/A"
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1048576), b""):
            h.update(c)
    return h.hexdigest()

def normalize_phone(t):
    if not t:
        return None
    digits = "".join(c for c in str(t) if c.isdigit())
    if not digits:
        return None
    # Algeria mobile: 07xx or 05xx (9 digits); strip leading 0 if 10 digits (FR-like) -> keep raw
    return digits

def main():
    parser = argparse.ArgumentParser(description="Merge OSM staging into production (dry-run by default).")
    parser.add_argument("--apply", action="store_true", help="Actually write inserts to production.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows processed.")
    args = parser.parse_args()

    # Pre-check production integrity & backup marker
    pconn = sqlite3.connect(PROD)
    pcur = pconn.cursor()
    pcur.execute("PRAGMA integrity_check")
    p_integ = pcur.fetchone()[0]
    pcur.execute("SELECT COUNT(*) FROM places")
    p_before = pcur.fetchone()[0]
    print("PROD integrity:", p_integ, "rows before:", p_before)

    sconn = sqlite3.connect(STAGING)
    scur = sconn.cursor()

    # Build set of existing place_ids from OSM source already in production
    existing = set()
    pcur.execute("SELECT place_id FROM places WHERE source LIKE 'osm_overpass%'")
    for row in pcur.fetchall():
        existing.add(str(row[0]))

    # Also check existing production: count rows with name NULL (as baseline)
    pcur.execute("SELECT COUNT(*) FROM places WHERE (nom IS NULL OR nom = '')")
    prod_name_missing = pcur.fetchone()[0]

    # Count staging candidates (excluding rows where name is NULL - required)
    scur.execute("SELECT COUNT(*) FROM osm_pilot_entries WHERE name IS NOT NULL AND name != ''")
    total_candidates = scur.fetchone()[0]
    print("STAGING candidates (name not null):", total_candidates)

    scur.execute("SELECT COUNT(*) FROM osm_pilot_entries WHERE name IS NULL OR name = ''")
    rejected_name_null = scur.fetchone()[0]

    # Fetch staging rows to process
    limit_clause = ""
    if args.limit:
        limit_clause = " LIMIT " + str(args.limit)
    scur.execute("SELECT osm_id, osm_type, wilaya, name, category, amenity, healthcare, "
            "lat, lon, tags, phone, address, website, source_provenance, collected_at "
            "FROM osm_pilot_entries WHERE name IS NOT NULL AND name != ''" + limit_clause)
    candidates = scur.fetchall()

    cols = ["osm_id","osm_type","wilaya","name","category","amenity","healthcare","lat","lon","tags","phone","address","website","source_provenance","collected_at"]

    # Map staging columns to production columns
    # places table columns: ... see PRAGMA table_info(places)
    # We map: name->nom, lat->latitude, lon->longitude, phone->telephone, address->adresse, website->site_web, wilaya->wilaya
    # place_id for OSM = "osm_overpass:type:id" to ensure uniqueness across sources
    inserted = 0
    skip_dup = 0
    skip_coord = 0
    skip_other = 0
    sample_inserts = []

    for row in candidates:
        d = dict(zip(cols, row))
        if d["lat"] is None or d["lon"] is None:
            skip_coord += 1
            continue
        # Build unique place_id from source
        place_id = "osm_overpass:" + str(d.get("osm_type")) + ":" + str(d.get("osm_id")) + ":" + str(d.get("wilaya"))
        # Check if already exists
        pcur.execute("SELECT 1 FROM places WHERE place_id = ?", (place_id,))
        if pcur.fetchone():
            skip_dup += 1
            continue
        # Validate coordinates are in Algeria roughly
        lat = d["lat"]; lon = d["lon"]
        if not (18.0 <= lat <= 38.0 and -9.0 <= lon <= 12.0):
            skip_coord += 1
            continue

        phone = normalize_phone(d["phone"])
        insert_row = (
            place_id,                    # place_id
            d.get("name"),               # nom
            None,                        # nom_normalized
            d.get("address"),            # adresse
            None,                        # adresse_normalized
            phone,                       # telephone
            None,                        # telephone_normalized
            d.get("phone"),              # telephone_raw
            d.get("website"),            # site_web
            None,                        # note
            None,                        # nombre_avis
            None,                        # horaires
            lat,                         # latitude
            lon,                         # longitude
            None,                        # google_maps_url
            str(d.get("amenity") or d.get("healthcare")),  # type_google
            d.get("wilaya"),             # wilaya
            None,                        # wilaya_normalized
            None,                        # commune
            str(d.get("category")),      # categorie_recherche
            "osm_overpass:" + str(d.get("osm_id")),  # source
            None,                        # scrape_date
            "active",                    # status
            None,                        # created_at
            None,                        # updated_at
            "VERIFIED",                  # name_status
            "osm_overpass",              # name_source
            None,                        # recovery_date
            None,                        # commune_source
            None,                        # commune_confidence
            None                         # commune_updated_at
        )

        if not args.apply:
            if len(sample_inserts) < 5:
                sample_inserts.append((place_id, d.get("name"), d.get("wilaya"), str(d.get("amenity") or d.get("healthcare"))))
            inserted += 1
        else:
            try:
                pcur.execute("""INSERT INTO places
                    (place_id, nom, nom_normalized, adresse, adresse_normalized,
                     telephone, telephone_normalized, telephone_raw, site_web, note, nombre_avis, horaires,
                     latitude, longitude, google_maps_url, type_google,
                     wilaya, wilaya_normalized, commune, categorie_recherche,
                     source, scrape_date, status, created_at, updated_at,
                     name_status, name_source, recovery_date,
                     commune_source, commune_confidence, commune_updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    insert_row)
                inserted += 1
            except Exception as e:
                skip_other += 1
                print("  insert error:", str(e)[:100])

    if args.apply:
        pconn.commit()
    else:
        pconn.rollback()

    # Post-check
    pcur.execute("SELECT COUNT(*) FROM places")
    p_after = pcur.fetchone()[0]
    pconn.close()
    sconn.close()

    print("DRY-RUN:", not args.apply)
    print("Candidates processed:", len(candidates))
    print("Would insert:", inserted)
    print("Skip duplicates (already in prod):", skip_dup)
    print("Skip missing coordinates:", skip_coord)
    print("Skip missing name (excluded already):", rejected_name_null)
    print("PROD rows after:", p_after, "(before:", p_before + inserted if args.apply else p_before, ")")
    if sample_inserts:
        print("Sample inserts:")
        for s in sample_inserts:
            sys.stdout.buffer.write(("  place_id: " + str(s[0]) + " name: " + str(s[1]) + " wilaya: " + str(s[2]) + " cat: " + str(s[3]) + "\n").encode("utf-8", errors="replace"))

if __name__ == "__main__":
    main()
