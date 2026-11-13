#!/usr/bin/env python3
"""Read-only GPS quality audit for MEDIZY SQLite database.
Never writes to the source database. Outputs JSON summary and CSV row-level findings.
"""
import sqlite3, csv, json, math, os
from collections import Counter, defaultdict
from datetime import datetime, timezone

DB = "assets/data/sante_dz_bundled.db"
OUT = "gps-audit-output"
os.makedirs(OUT, exist_ok=True)
con = sqlite3.connect("file:" + DB + "?mode=ro", uri=True)
con.row_factory = sqlite3.Row
tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
if "facilities" not in tables:
    raise SystemExit("ERROR: table facilities is missing")
cols = {r["name"] for r in con.execute("PRAGMA table_info(facilities)")}
wanted = ["id","nom","name","latitude","longitude","place_id","source","commune","wilaya","wilaya_code"]
selected = [c for c in wanted if c in cols]
rows = con.execute("SELECT " + ", ".join('"' + c + '"' for c in selected) + " FROM facilities").fetchall()
communes = {}
if "communes" in tables:
    cc = {r["name"] for r in con.execute("PRAGMA table_info(communes)")}
    needed = {"wilaya_code","nom_fr","latitude","longitude"}
    if needed.issubset(cc):
        for r in con.execute("SELECT wilaya_code, nom_fr, latitude, longitude FROM communes"):
            if r["latitude"] is not None and r["longitude"] is not None:
                communes[(str(r["wilaya_code"]), str(r["nom_fr"]).strip().casefold())] = (float(r["latitude"]), float(r["longitude"]))
def hav(a,b,c,d):
    p1,p2=math.radians(a),math.radians(c); dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371000*2*math.atan2(math.sqrt(x),math.sqrt(max(0,1-x)))
def val(r,k): return r[k] if k in r.keys() else None

sources=Counter(); place_ids=Counter(); coord_counts=Counter()
missing=invalid=outside=0; centroid_dist=[]; exact_centroid=0
details=[]
for r in rows:
    lat,lon=val(r,"latitude"),val(r,"longitude")
    src=str(val(r,"source") or "NON RENSEIGNÉ")
    sources[src]+=1
    pid=val(r,"place_id")
    if pid: place_ids[str(pid)]+=1
    valid = lat is not None and lon is not None
    status=[]
    if not valid:
        missing+=1; status.append("GPS_MANQUANT")
    else:
        try: lat=float(lat); lon=float(lon)
        except (TypeError,ValueError): valid=False; invalid+=1; status.append("GPS_NON_NUMERIQUE")
        if valid:
            if not (math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):
                invalid+=1; status.append("GPS_HORS_LIMITES_GLOBALES")
            else:
                coord_counts[(round(lat,6),round(lon,6))]+=1
                if not (18<=lat<=38 and -9<=lon<=12):
                    outside+=1; status.append("HORS_EMPRISE_ALGERIE_A_VERIFIER")
                wc=val(r,"wilaya_code"); com=val(r,"commune")
                ref=communes.get((str(wc),str(com).strip().casefold())) if wc is not None and com else None
                if ref:
                    d=hav(lat,lon,ref[0],ref[1]); centroid_dist.append(d)
                    if d<2: exact_centroid+=1; status.append("SUR_CENTROIDE_COMMUNAL")
                    elif d<100: status.append("A_MOINS_100M_DU_CENTROIDE")
    details.append({
        "id":val(r,"id"),"nom":val(r,"nom") or val(r,"name"),"wilaya":val(r,"wilaya") or val(r,"wilaya_code"),
        "commune":val(r,"commune"),"latitude":val(r,"latitude"),"longitude":val(r,"longitude"),
        "place_id":pid,"source":src,"audit_flags":";".join(status) if status else "AUCUN_DRAPEAU_AUTOMATIQUE"
    })
duplicates=[{"place_id":k,"count":v} for k,v in place_ids.items() if v>1]
coord_dupes=[{"latitude":k[0],"longitude":k[1],"count":v} for k,v in coord_counts.items() if v>1]
coord_dupes.sort(key=lambda x:x["count"],reverse=True)
with open(os.path.join(OUT,"gps-audit-facilities.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=list(details[0].keys()) if details else ["id"]); w.writeheader(); w.writerows(details)
summary={
 "generated_utc":datetime.now(timezone.utc).isoformat(),
 "database":"assets/data/sante_dz_bundled.db",
 "read_only":True,"total_facilities":len(rows),"columns_found":selected,
 "missing_gps":missing,"invalid_gps":invalid,"outside_approx_algeria_bounds":outside,
 "distinct_coordinate_pairs_6dp":len(coord_counts),
 "coordinate_pairs_shared_by_multiple_facilities":len(coord_dupes),
 "rows_in_shared_coordinate_pairs":sum(x["count"] for x in coord_dupes),
 "duplicate_place_id_values":len(duplicates),
 "rows_with_duplicate_place_id":sum(x["count"] for x in duplicates),
 "commune_reference_matches":len(centroid_dist),
 "within_2m_of_commune_centroid":exact_centroid,
 "centroid_distance_median":sorted(centroid_dist)[len(centroid_dist)//2] if centroid_dist else None,
 "centroid_distance_p90":sorted(centroid_dist)[int((len(centroid_dist)-1)*.9)] if centroid_dist else None,
 "source_counts":dict(sources),
 "top_shared_coordinates":coord_dupes[:100],
 "duplicate_place_ids_sample":duplicates[:100],
 "interpretation":"This is a structural GPS audit, not a Google Maps verification. Coordinates near commune centroids are not proof of facility-level accuracy. Independent Google Maps matching requires a trusted external reference dataset keyed by stable place_id."
}
with open(os.path.join(OUT,"gps-audit-summary.json"),"w",encoding="utf-8") as f: json.dump(summary,f,ensure_ascii=False,indent=2)
print(json.dumps(summary,ensure_ascii=False,indent=2))
con.close()
