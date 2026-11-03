#!/usr/bin/env python3
"""Download Algeria Overture Places and retain healthcare POI candidates in staging.

This is a source-only extractor: it never reads or writes the MEDIZY production DB.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Conservative national bbox covering Algeria; final coordinate validation is repeated.
ALGERIA_BBOX = "-8.67,18.96,12.00,37.12"
FIELDS = [
    "source", "source_id", "name", "category", "latitude", "longitude",
    "phone", "website", "address", "wilaya", "commune", "source_url",
    "license", "review_status", "source_category"
]
HEALTH_TERMS = (
    "hospital", "clinic", "pharmacy", "doctor", "dentist", "health",
    "medical", "healthcare", "laboratory", "nursing"
)
CATEGORY_MAP = {
    "hospital": "hospital", "clinic": "clinic", "pharmacy": "pharmacy",
    "doctor": "medical_practice", "dentist": "dental_practice",
    "medical": "medical_center", "health": "health_center",
    "laboratory": "medical_laboratory", "nursing": "health_center",
}

def nested_values(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"primary", "alternate", "value", "label", "name"} and isinstance(child, (str, int, float)):
                yield str(child)
            else:
                yield from nested_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_values(child)

def get_path(obj, *path):
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur

def category_for(props):
    taxonomy = props.get("taxonomy") or {}
    candidates = list(nested_values(taxonomy))
    candidates += [str(props.get(k, "")) for k in ("category", "primary_category", "type")]
    raw = " | ".join(x for x in candidates if x).strip()
    low = raw.casefold()
    if not any(term in low for term in HEALTH_TERMS):
        return "", raw
    for term, category in CATEGORY_MAP.items():
        if term in low:
            return category, raw
    return "health_center", raw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geojson", default="data/source/overture_algeria_places.geojson")
    ap.add_argument("--output", default="data/staging/overture_algeria_healthcare.csv")
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()
    geojson = Path(args.geojson)
    geojson.parent.mkdir(parents=True, exist_ok=True)
    if args.download or not geojson.exists():
        cmd = [
            sys.executable, "-m", "overturemaps", "download",
            f"--bbox={ALGERIA_BBOX}", "-f", "geojson",
            "--type=place", "-o", str(geojson)
        ]
        subprocess.run(cmd, check=True)
    payload = json.loads(geojson.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    rows, counts = {}, Counter()
    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        try:
            lon, lat = float(lon), float(lat)
        except (TypeError, ValueError):
            continue
        if not (18.0 <= lat <= 38.0 and -9.0 <= lon <= 13.0):
            continue
        category, raw_category = category_for(props)
        if not category:
            continue
        names = props.get("names") or {}
        name = names.get("primary") if isinstance(names, dict) else ""
        name = name or props.get("name") or ""
        if isinstance(name, dict):
            name = name.get("value", "")
        if not str(name).strip():
            counts["missing_name"] += 1
            continue
        place_id = str(props.get("id") or feature.get("id") or "")
        if not place_id:
            counts["missing_id"] += 1
            continue
        addresses = props.get("addresses") or []
        address = ""
        if addresses and isinstance(addresses[0], dict):
            address = addresses[0].get("freeform") or ""
        contacts = props.get("socials") or []
        phone = props.get("phone") or props.get("tel") or ""
        website = props.get("website") or ""
        row = {
            "source": "Overture Maps Places",
            "source_id": place_id,
            "name": str(name).strip(),
            "category": category,
            "latitude": lat,
            "longitude": lon,
            "phone": phone,
            "website": website,
            "address": address,
            "wilaya": "",
            "commune": "",
            "source_url": "https://overturemaps.org/",
            "license": "See Overture provider/license provenance for this feature",
            "review_status": "needs_verification",
            "source_category": raw_category[:500],
        }
        rows[place_id] = row
        counts[category] += 1
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows.values())
    report = {
        "source": "Overture Maps Places",
        "bbox": ALGERIA_BBOX,
        "raw_features": len(features),
        "unique_healthcare_candidates": len(rows),
        "by_category": dict(counts),
        "output": str(out),
        "production_database_modified": False,
        "warning": "This GeoJSON download may contain only features with point geometries. Inspect Overture taxonomy and per-feature provider/license provenance before reuse; candidates require deduplication and human verification."
    }
    report_path = out.with_name("overture_quality_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
