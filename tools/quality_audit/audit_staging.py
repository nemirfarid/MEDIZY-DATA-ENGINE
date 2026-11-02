#!/usr/bin/env python3
"""Audit staging CSV candidates without modifying any MEDIZY production data."""
from __future__ import annotations
import argparse, csv, json, re
from collections import Counter
from pathlib import Path

FALSE_POSITIVE = re.compile(
    r"conseil constitutionnel|en alg[eé]rie$|liste des|annuaire|"
    r"minist[eè]re|direction de la sant[eé]|sant[eé] publique$",
    re.I
)
GENERIC = re.compile(
    r"^(h[oô]pital|clinique|pharmacie|polyclinique|centre de sant[eé]|"
    r"salle de soins|cabinet m[eé]dical)$", re.I
)
ALLOWED = {
    "hospital", "clinic", "pharmacy", "medical_practice",
    "dental_practice", "health_center", "medical_center",
    "medical_laboratory", "health_post"
}
FIELDS = [
    "source","source_id","name","category","latitude","longitude",
    "phone","website","address","wilaya","commune","source_url",
    "license","review_status","audit_flags"
]

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def norm(v):
    return re.sub(r"\\s+", " ", (v or "").strip()).casefold()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="data/staging/audited_candidates.csv")
    ap.add_argument("--report", default="data/staging/quality_report.json")
    ap.add_argument("--master", help="Optional existing MEDIZY CSV export; read-only")
    a=ap.parse_args()
    rows=read_csv(a.input)
    master=read_csv(a.master) if a.master else []
    master_ids={(norm(r.get("source")), norm(r.get(k))) for r in master for k in ("source_id","place_id","osm_id","wikidata_id") if r.get(k)}
    seen=set(); accepted=[]; rejected=Counter(); flags_count=Counter()
    for r in rows:
        name=(r.get("name") or r.get("name_fr") or r.get("name_ar") or "").strip()
        cat=norm(r.get("category"))
        flags=[]
        sid=(r.get("source_id") or r.get("wikidata_id") or r.get("osm_id") or "").strip()
        if not name or GENERIC.match(name): flags.append("generic_or_missing_name")
        if FALSE_POSITIVE.search(name): flags.append("likely_non_facility_or_directory")
        if cat not in ALLOWED: flags.append("unsupported_or_nonclinical_category")
        try:
            lat=float(r.get("latitude") or "")
            lon=float(r.get("longitude") or "")
            if not (18.0 <= lat <= 38.0 and -9.0 <= lon <= 13.0):
                flags.append("coordinates_outside_algeria_bbox")
        except (ValueError, TypeError):
            flags.append("missing_coordinates")
        if not sid: flags.append("missing_source_identifier")
        key=(norm(r.get("source")),norm(sid)) if sid else None
        if key and key in seen: flags.append("duplicate_source_identifier")
        if key: seen.add(key)
        if sid and (norm(r.get("source")), norm(sid)) in master_ids: flags.append("already_in_master_by_identifier")
        for f in flags: flags_count[f]+=1
        if flags:
            rejected.update(flags)
            continue
        accepted.append({
            "source":r.get("source",""),"source_id":sid,"name":name,
            "category":cat,"latitude":r.get("latitude",""),"longitude":r.get("longitude",""),
            "phone":r.get("phone",""),"website":r.get("website",""),
            "address":r.get("address",""),"wilaya":r.get("wilaya",r.get("admin_entity","")),
            "commune":r.get("commune",""),"source_url":r.get("source_url",""),
            "license":r.get("license",""),"review_status":"candidate_needs_human_review",
            "audit_flags":""
        })
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(accepted)
    report={
        "input_file":a.input,"input_rows":len(rows),
        "accepted_candidate_rows":len(accepted),
        "rejected_rows":len(rows)-len(accepted),
        "rejection_flag_counts":dict(rejected),
        "master_comparison_performed":bool(a.master),
        "master_rows_read_only":len(master),
        "production_database_modified":False,
        "warning":"Passing automated checks does not prove a facility exists or is new. Human verification is required."
    }
    rp=Path(a.report); rp.parent.mkdir(parents=True,exist_ok=True)
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
