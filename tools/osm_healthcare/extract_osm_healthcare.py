#!/usr/bin/env python3
"""Extract clinical healthcare objects from Geofabrik Algeria OSM PBF.

Staging only: never reads or writes the MEDIZY production database.
OSM data is ODbL 1.0; retain attribution and review share-alike obligations.
"""
from __future__ import annotations
import argparse, csv, json, urllib.request
from pathlib import Path
import osmium

PBF_URL = "https://download.geofabrik.de/africa/algeria-latest.osm.pbf"
FIELDS = [
    "source", "source_id", "osm_type", "osm_id", "name", "name_fr", "name_ar",
    "category", "healthcare", "amenity", "shop", "speciality", "operator",
    "phone", "website", "opening_hours", "address", "wilaya", "commune",
    "latitude", "longitude", "geometry_method", "source_url", "license",
    "review_status"
]
# Deliberately excludes veterinary, social services, nursing homes and suppliers.
def first(tags, *keys):
    for key in keys:
        value = tags.get(key)
        if value:
            return value
    return ""

def classify(t):
    h, a = t.get("healthcare", ""), t.get("amenity", "")
    if a == "pharmacy" or h == "pharmacy": return "pharmacy"
    if a == "hospital" or h == "hospital": return "hospital"
    if a == "clinic" or h in {"clinic", "clinic;doctor"}: return "clinic"
    if a == "doctors" or h in {"doctor", "doctors"}: return "medical_practice"
    if a == "dentist" or h == "dentist": return "dental_practice"
    if h in {"health_centre", "health_center", "centre"}: return "health_center"
    if h in {"laboratory", "medical_laboratory"}: return "medical_laboratory"
    if h in {"rehabilitation", "physiotherapist"}: return "medical_practice"
    if a == "health_post" or h == "health_post": return "health_post"
    return ""

def coordinates(obj):
    try:
        if obj.is_node():
            return obj.location.lat, obj.location.lon, "osm_node"
        locs = [n.location for n in obj.nodes if n.location.valid()]
        if locs:
            return sum(p.lat for p in locs)/len(locs), sum(p.lon for p in locs)/len(locs), "way_node_average"
    except Exception:
        pass
    return "", "", "relation_geometry_not_resolved"

class Handler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.rows = {}
        self.relations_skipped_geometry = 0
    def add(self, obj, kind):
        t = obj.tags
        category = classify(t)
        if not category: return
        lat, lon, method = coordinates(obj)
        osm_id = str(obj.id)
        key = f"{kind}/{osm_id}"
        self.rows[key] = {
            "source":"OpenStreetMap via Geofabrik", "source_id":key,
            "osm_type":kind, "osm_id":osm_id,
            "name":first(t,"name","official_name"),
            "name_fr":t.get("name:fr",""), "name_ar":t.get("name:ar",""),
            "category":category, "healthcare":t.get("healthcare",""),
            "amenity":t.get("amenity",""), "shop":t.get("shop",""),
            "speciality":first(t,"healthcare:speciality","medical_specialty"),
            "operator":t.get("operator",""),
            "phone":first(t,"contact:phone","phone"),
            "website":first(t,"contact:website","website"),
            "opening_hours":t.get("opening_hours",""),
            "address":" ".join(x for x in [
                t.get("addr:housenumber",""), t.get("addr:street",""),
                t.get("addr:suburb",""), t.get("addr:city","")
            ] if x),
            "wilaya":first(t,"addr:state","is_in:state"),
            "commune":first(t,"addr:city","addr:town","addr:village"),
            "latitude":lat, "longitude":lon, "geometry_method":method,
            "source_url":f"https://www.openstreetmap.org/{kind}/{osm_id}",
            "license":"ODbL 1.0", "review_status":"needs_verification"
        }
    def node(self, n): self.add(n,"node")
    def way(self, w): self.add(w,"way")
    def relation(self, r):
        # Relations need a proper area/centroid pass. Do not emit blank-coordinate
        # records that could be mistaken for usable facilities.
        if classify(r.tags):
            self.relations_skipped_geometry += 1

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pbf", default="data/source/algeria-latest.osm.pbf")
    p.add_argument("--output", default="data/staging/osm_algeria_healthcare.csv")
    p.add_argument("--download", action="store_true")
    a=p.parse_args()
    pbf=Path(a.pbf); pbf.parent.mkdir(parents=True,exist_ok=True)
    if a.download:
        req=urllib.request.Request(PBF_URL,headers={"User-Agent":"MEDIZY-Data-Engine/1.0 (open-data research)"})
        with urllib.request.urlopen(req,timeout=180) as r, pbf.open("wb") as f:
            while True:
                chunk=r.read(1024*1024)
                if not chunk: break
                f.write(chunk)
    if not pbf.exists(): raise SystemExit(f"PBF absent: {pbf}; use --download")
    h=Handler(); h.apply_file(str(pbf), locations=True)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader()
        w.writerows(sorted(h.rows.values(),key=lambda x:(x["category"],x["wilaya"],x["name"])))
    summary={}
    unresolved=0
    for row in h.rows.values():
        summary[row["category"]]=summary.get(row["category"],0)+1
        if not row["latitude"]: unresolved += 1
    print(json.dumps({"unique_osm_objects":len(h.rows),"by_category":summary,
      "relation_or_geometry_unresolved":unresolved,
      "classified_relations_skipped_pending_geometry":h.relations_skipped_geometry,
      "csv":str(out),
      "production_database_modified":False},ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
