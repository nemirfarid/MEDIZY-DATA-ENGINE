#!/usr/bin/env python3
"""Collect candidate Algerian healthcare entities from Wikidata into isolated staging."""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "MEDIZY-Data-Engine/1.1 (open-data research; https://github.com/nemirfarid/MEDIZY-DATA-ENGINE)"
# Query each class separately: avoid the expensive transitive subclass path that
# previously caused WDQS HTTP 504 timeouts.
CLASSES = {
    "Q16917": "hospital",
    "Q1774898": "clinic",
    "Q131734": "pharmacy",
    "Q13218630": "medical_center",
    "Q4287745": "health_center",
    "Q3355359": "medical_laboratory",
    "Q178706": "nursing_home",
}
FIELDS = [
    "source", "source_id", "wikidata_id", "name", "name_fr", "name_ar",
    "category", "latitude", "longitude", "phone", "website", "address",
    "admin_entity", "commune", "source_url", "license", "review_status"
]

def build_query(class_qid: str) -> str:
    return f"""
SELECT DISTINCT ?item ?labelFr ?labelEn ?labelAr ?coord ?phone ?website ?address ?admin WHERE {{
  ?item wdt:P17 wd:Q262;
        wdt:P31 wd:{class_qid}.
  OPTIONAL {{ ?item wdt:P625 ?coord. }}
  OPTIONAL {{ ?item wdt:P1329 ?phone. }}
  OPTIONAL {{ ?item wdt:P856 ?website. }}
  OPTIONAL {{ ?item wdt:P6375 ?address. }}
  OPTIONAL {{ ?item wdt:P131 ?admin. }}
  OPTIONAL {{ ?item rdfs:label ?labelFr FILTER(LANG(?labelFr)="fr") }}
  OPTIONAL {{ ?item rdfs:label ?labelEn FILTER(LANG(?labelEn)="en") }}
  OPTIONAL {{ ?item rdfs:label ?labelAr FILTER(LANG(?labelAr)="ar") }}
}}
LIMIT 2000
"""

def request_rows(class_qid: str, retries: int = 4):
    query = build_query(class_qid)
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=75) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload["results"]["bindings"]
        except urllib.error.HTTPError as exc:
            # WDQS may temporarily return 429/5xx when busy. Retry gently.
            if attempt + 1 == retries or (exc.code not in (429, 500, 502, 503, 504)):
                raise
            time.sleep(8 * (attempt + 1))
        except (TimeoutError, urllib.error.URLError):
            if attempt + 1 == retries:
                raise
            time.sleep(8 * (attempt + 1))
    return []

def val(row, key):
    return row.get(key, {}).get("value", "")

def parse_coord(value):
    try:
        inside = value[value.index("(") + 1:value.index(")")]
        lon, lat = inside.split()[:2]
        return lat, lon
    except Exception:
        return "", ""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/staging/wikidata_algeria_healthcare.csv")
    args = parser.parse_args()
    unique = {}
    per_class = {}
    for index, (class_qid, category) in enumerate(CLASSES.items()):
        bindings = request_rows(class_qid)
        per_class[category] = len(bindings)
        for row in bindings:
            uri = val(row, "item")
            qid = uri.rsplit("/", 1)[-1]
            if not qid:
                continue
            lat, lon = parse_coord(val(row, "coord"))
            item = {
                "source": "Wikidata",
                "source_id": qid,
                "wikidata_id": qid,
                "name": val(row, "labelFr") or val(row, "labelEn") or val(row, "labelAr"),
                "name_fr": val(row, "labelFr"),
                "name_ar": val(row, "labelAr"),
                "category": category,
                "latitude": lat,
                "longitude": lon,
                "phone": val(row, "phone"),
                "website": val(row, "website"),
                "address": val(row, "address"),
                "admin_entity": val(row, "admin"),
                "commune": "",
                "source_url": f"https://www.wikidata.org/wiki/{qid}",
                "license": "CC0",
                "review_status": "needs_verification",
            }
            score = sum(bool(item[k]) for k in ("name", "latitude", "longitude", "phone", "website", "address", "admin_entity"))
            if qid not in unique or score > unique[qid][0]:
                unique[qid] = (score, item)
        # Be polite to the public endpoint between independent class queries.
        if index < len(CLASSES) - 1:
            time.sleep(2)
    rows = [entry[1] for entry in unique.values()]
    rows.sort(key=lambda x: (x["admin_entity"], x["name"], x["wikidata_id"]))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "source": "Wikidata Query Service",
        "raw_rows_by_class": per_class,
        "unique_wikidata_items": len(rows),
        "with_coordinates": sum(bool(r["latitude"] and r["longitude"]) for r in rows),
        "with_phone": sum(bool(r["phone"]) for r in rows),
        "with_website": sum(bool(r["website"]) for r in rows),
        "csv": str(output),
        "production_database_modified": False,
        "warning": "Direct instance classes only; incomplete coverage. Candidates require verification and deduplication."
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
