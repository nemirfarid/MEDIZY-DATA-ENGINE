#!/usr/bin/env python3
"""Conservative MEDIZY staging audit and merge.

Never writes to a production database. Inputs are CSV exports; outputs are
staging CSVs and a JSON quality report. Facility and practitioner records
must remain separate.
"""
from __future__ import annotations
import argparse, csv, json, re, unicodedata
from collections import Counter
from pathlib import Path

FACILITY_HINTS = {"pharmacy","hospital","clinic","doctors","dentist","health_centre",
                  "health_post","nursing_home","laboratory","medical"}
PRACTITIONER_HINTS = {"doctor","physician","dentist","nurse","midwife","pharmacist",
                      "physiotherapist","psychologist","optometrist"}

def norm(value):
    s = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def classify(row):
    tags = " ".join(norm(row.get(k)) for k in
                    ("category","healthcare","amenity","shop","speciality","type"))
    if any(x in tags for x in ("doctor","physician","dentist","nurse","midwife",
                               "pharmacist","physiotherapist","psychologist")):
        # A doctor's office is a facility record, not a named practitioner.
        if norm(row.get("name")) and any(x in tags for x in ("clinic","hospital","pharmacy","amenity")):
            return "facility"
        return "practitioner_candidate"
    return "facility"

def stable_key(r):
    sid = norm(r.get("source_id") or r.get("osm_id") or r.get("id"))
    if sid:
        return f"source:{norm(r.get('source'))}:{sid}"
    name = norm(r.get("name") or r.get("name_fr") or r.get("name_ar"))
    lat, lon = norm(r.get("latitude") or r.get("lat")), norm(r.get("longitude") or r.get("lon"))
    if name and lat and lon:
        return f"geo:{name}:{lat[:10]}:{lon[:10]}"
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True, help="CSV input (repeatable)")
    ap.add_argument("--out-dir", default="data/staging/audit")
    args = ap.parse_args()
    rows = []
    for p in args.input:
        for r in read_csv(p):
            r.setdefault("source_file", Path(p).name)
            rows.append(r)
    facilities, practitioners, review = [], [], []
    seen = set()
    duplicate_count = 0
    for r in rows:
        typ = classify(r)
        key = stable_key(r)
        if key and key in seen:
            duplicate_count += 1
            continue
        if key:
            seen.add(key)
        name = r.get("name") or r.get("name_fr") or r.get("name_ar")
        lat = r.get("latitude") or r.get("lat")
        lon = r.get("longitude") or r.get("lon")
        if typ == "practitioner_candidate":
            r["record_type"] = typ
            practitioners.append(r)
        else:
            r["record_type"] = "facility"
            facilities.append(r)
        if not name or not lat or not lon:
            review.append({"source_file":r.get("source_file"),"source_id":r.get("source_id"),
                           "name":name,"missing_name":not bool(name),
                           "missing_coordinates":not (lat and lon)})
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    def write(name, data):
        if not data: return
        fields = sorted(set().union(*(x.keys() for x in data)))
        with open(out/name,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(data)
    write("facilities_staging.csv",facilities)
    write("practitioner_candidates_staging.csv",practitioners)
    write("records_needing_review.csv",review)
    report = {
      "input_files": args.input, "input_rows":len(rows),
      "facility_records_after_exact_source_dedup":len(facilities),
      "practitioner_candidates_after_exact_source_dedup":len(practitioners),
      "duplicate_source_keys_removed":duplicate_count,
      "records_needing_review":len(review),
      "production_database_modified":False,
      "warning":"This is a conservative staging audit, not proof of real-world uniqueness or professional registration."
    }
    (out/"quality_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
