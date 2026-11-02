#!/usr/bin/env python3
"""Collect Algerian healthcare entities from Wikidata Query Service.

Wikidata is CC0. This produces a source-attributed staging CSV only; it never
writes to MEDIZY or merges records automatically. Public WDQS has rate limits.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "MEDIZY-Data-Engine/1.0 (open-data directory research; contact: repository maintainer)"
FIELDS = [
    "source", "source_id", "wikidata_id", "name", "name_fr", "name_ar",
    "category", "latitude", "longitude", "phone", "website", "address",
    "wilaya", "commune", "source_url", "license", "review_status"
]

QUERY = """
SELECT ?item ?itemLabel ?itemLabelFr ?itemLabelAr ?coord ?phone ?website
       ?address ?adminLabel ?instanceLabel WHERE {
  ?item wdt:P17 wd:Q262;
        wdt:P31/wdt:P279* ?class.
  VALUES ?class {
    wd:Q16917 wd:Q1774898 wd:Q131734 wd:Q13218630
    wd:Q4287745 wd:Q3355359 wd:Q178706
  }
  OPTIONAL { ?item wdt:P625 ?coord. }
  OPTIONAL { ?item wdt:P1329 ?phone. }
  OPTIONAL { ?item wdt:P856 ?website. }
  OPTIONAL { ?item wdt:P6375 ?address. }
  OPTIONAL { ?item wdt:P131 ?admin. }
  OPTIONAL { ?item wdt:P31 ?instance. }
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "fr,en,ar".
    ?item rdfs:label ?itemLabel.
    ?admin rdfs:label ?adminLabel.
    ?instance rdfs:label ?instanceLabel.
  }
  OPTIONAL { ?item rdfs:label ?itemLabelFr FILTER(LANG(?itemLabelFr)="fr") }
  OPTIONAL { ?item rdfs:label ?itemLabelAr FILTER(LANG(?itemLabelAr)="ar") }
}
LIMIT 10000
"""

def request_rows(retries: int = 4):
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": QUERY, "format": "json"})
    req = urllib.request.Request(url, headers={
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload["results"]["bindings"]
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(3 * (attempt + 1))
    return []

def val(row, key):
    return row.get(key, {}).get("value", "")

def parse_coord(value):
    # Wikidata coordinate lexical form: Point(longitude latitude)
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
    bindings = request_rows()
    unique = {}
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
            "name": val(row, "itemLabel"),
            "name_fr": val(row, "itemLabelFr"),
            "name_ar": val(row, "itemLabelAr"),
            "category": val(row, "instanceLabel") or "healthcare_entity",
            "latitude": lat,
            "longitude": lon,
            "phone": val(row, "phone"),
            "website": val(row, "website"),
            "address": val(row, "address"),
            "wilaya": val(row, "adminLabel"),
            "commune": "",
            "source_url": f"https://www.wikidata.org/wiki/{qid}",
            "license": "CC0",
            "review_status": "needs_verification",
        }
        # Keep the most complete row when optional multi-valued properties expand joins.
        score = sum(bool(item[k]) for k in ("name", "latitude", "longitude", "phone", "website", "address", "wilaya"))
        if qid not in unique or score > unique[qid][0]:
            unique[qid] = (score, item)
    rows = [entry[1] for entry in unique.values()]
    rows.sort(key=lambda x: (x["wilaya"], x["name"], x["wikidata_id"]))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "source": "Wikidata Query Service",
        "raw_rows": len(bindings),
        "unique_wikidata_items": len(rows),
        "with_coordinates": sum(bool(r["latitude"] and r["longitude"]) for r in rows),
        "with_phone": sum(bool(r["phone"]) for r in rows),
        "with_website": sum(bool(r["website"]) for r in rows),
        "csv": str(output),
        "production_database_modified": False,
        "warning": "Coverage is incomplete; results are candidates, not a verified national register."
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
