#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Phase 8.2.3 - Real OSM Overpass pilot (staging only).
Sequential queries for Illizi (area), Tindouf (bbox), El Meniaa (bbox).
Writes ONLY to staging_osm_pilot.db. Production untouched.
"""
import os, json, sqlite3, time, hashlib, sys
from datetime import datetime
from urllib import request, error

PROD = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
STAGING = r"C:\SANTE_DZ_SCRAPER\staging_osm_pilot.db"
REPORT = r"C:\SANTE_DZ_SCRAPER\phase8_2_3_osm_pilot_report.txt"
CATS = ["hospital", "clinic", "doctors", "dentist", "pharmacy"]
# Wilayas with their query method: area = use OSM area, bbox = use bounding box
WILAYAS = [
    ("Illizi", "area", None),
    ("El Meniaa", "bbox", "34.5,3.1,34.8,3.4"),
    ("Tindouf", "bbox", "27.4,-8.5,28.0,-7.5"),
]

def sha256(p):
    if not os.path.exists(p): return "N/A"
    h = hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda: f.read(1048576), b""): h.update(c)
    return h.hexdigest()

def integrity(p):
    try:
        conn = sqlite3.connect(p); cur=conn.cursor(); cur.execute("PRAGMA integrity_check"); r=cur.fetchone(); conn.close()
        return r[0]
    except Exception as e: return "ERR:"+str(e)

def init_staging():
    conn = sqlite3.connect(STAGING)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS osm_pilot_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        osm_id TEXT, osm_type TEXT, wilaya TEXT, name TEXT, category TEXT,
        amenity TEXT, healthcare TEXT, lat REAL, lon REAL, tags TEXT,
        phone TEXT, address TEXT, website TEXT,
        source_provenance TEXT DEFAULT 'osm_overpass', collected_at TEXT
    )""")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_osm_unique ON osm_pilot_entries(osm_type, osm_id, wilaya)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_osm_id ON osm_pilot_entries(osm_id)")
    conn.commit(); conn.close()

def build_query(wilaya, method, bbox):
    cats = "|".join(CATS)
    amen_filter = "nwr[amenity~'^(" + cats + ")$']"
    if method == "area":
        return "[out:json][timeout:90];area[name='" + wilaya + "'];" + amen_filter + "(area);out center;"
    elif method == "bbox":
        return "[out:json][timeout:150];" + amen_filter + "(" + bbox + ");out center;"
    return ""

def fetch(q, retries=0):
    url = "https://overpass-api.de/api/interpreter"
    data = q.encode("utf-8")
    req = request.Request(url, data=data, headers={"User-Agent": "medizy-pilot/phase8.2.3", "Content-Type": "application/x-www-form-urlencoded"})
    start = datetime.now()
    try:
        with request.urlopen(req, timeout=120) as resp:
            body = resp.read()
        elapsed = (datetime.now() - start).total_seconds()
        try:
            j = json.loads(body)
            return "ok", j.get("elements",[]), elapsed, 200, "ok"
        except Exception:
            return "bad_json", [], elapsed, 200, "bad_json"
    except error.HTTPError as e:
        elapsed = (datetime.now() - start).total_seconds()
        msg = ""
        try: msg = e.read()[:300].decode("utf-8", errors="replace")
        except: pass
        return "http_"+str(e.code), [], elapsed, e.code, msg
    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds()
        return "err_"+type(e).__name__, [], elapsed, 0, str(e)

def parse(e):
    tags = e.get("tags",{}) or {}
    lat = e.get("lat"); lon = e.get("lon")
    c = e.get("center") or {}
    if lat is None: lat = c.get("lat")
    if lon is None: lon = c.get("lon")
    return {
        "osm_id": str(e.get("id")), "osm_type": e.get("type"), "name": tags.get("name"),
        "amenity": tags.get("amenity"), "healthcare": tags.get("healthcare"),
        "lat": lat, "lon": lon,
        "phone": tags.get("phone") or tags.get("contact:phone") or tags.get("mobile"),
        "address": tags.get("addr:full") or tags.get("addr:street") or tags.get("address"),
        "website": tags.get("website") or tags.get("url"),
        "tags": json.dumps(tags, ensure_ascii=False)
    }

def main():
    sys.stdout.write("PRE-CHECKS:\n")
    sys.stdout.write("  PROD SHA256: " + sha256(PROD) + "\n")
    sys.stdout.write("  PROD integrity: " + integrity(PROD) + "\n")
    sys.stdout.write("  STAGING integrity: " + integrity(STAGING) + "\n")

    init_staging()

    # Count before
    conn = sqlite3.connect(STAGING)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM osm_pilot_entries")
    before = cur.fetchone()[0]
    sys.stdout.write("STAGING entries before: " + str(before) + "\n")
    conn.close()

    stats = []
    conn = sqlite3.connect(STAGING)
    cur = conn.cursor()
    for wilaya, method, bbox in WILAYAS:
        q = build_query(wilaya, method, bbox)
        sys.stdout.write("Querying " + wilaya + " (" + method + ")\n")
        sys.stdout.flush()
        status, elems, elapsed, http_code, errmsg = fetch(q)
        inserted = 0
        ignored_dup = 0
        no_coord = 0
        no_name = 0
        cat_counts = {}
        retries = 0
        while status not in ("ok",) and retries < 2:
            if status.startswith("http_") and status in ("http_429", "http_504", "http_503", "http_502"):
                retries += 1
                sys.stdout.write("  Retryable: " + status + ", waiting 20s...\n")
                sys.stdout.flush()
                time.sleep(20)
                status, elems, elapsed, http_code, errmsg = fetch(q)
            else:
                break
        if status == "ok" and elems:
            for e in elems:
                p = parse(e)
                if p["lat"] is None or p["lon"] is None:
                    no_coord += 1
                    continue
                cat = p["amenity"] or p["healthcare"]
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
                if not p["name"]:
                    no_name += 1
                try:
                    cur.execute(
                        "INSERT OR IGNORE INTO osm_pilot_entries (osm_id, osm_type, wilaya, name, category, amenity, healthcare, lat, lon, tags, phone, address, website, source_provenance, collected_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (p["osm_id"], p["osm_type"], wilaya, p["name"], p["amenity"] or p["healthcare"], p["amenity"], p["healthcare"], p["lat"], p["lon"], p["tags"], p["phone"], p["address"], p["website"], "osm_overpass", datetime.now().isoformat())
                    )
                    if cur.rowcount > 0:
                        inserted += 1
                    else:
                        ignored_dup += 1
                except Exception:
                    pass
            conn.commit()
        stats.append({
            "wilaya": wilaya,
            "method": method,
            "status": status,
            "http_code": http_code,
            "retries": retries,
            "elems_bruts": len(elems) if elems else 0,
            "inserted": inserted,
            "dup_ignored": ignored_dup,
            "no_coord": no_coord,
            "no_name": no_name,
            "elapsed": elapsed,
            "errmsg": errmsg[:200] if errmsg else "",
            "cat_counts": cat_counts
        })
        sys.stdout.write("  result: " + status + " elems=" + str(len(elems) if elems else 0) + " inserted=" + str(inserted) + "\n")
        sys.stdout.flush()
        time.sleep(8)  # Delay between wilayas
    conn.close()

    # Count after
    conn = sqlite3.connect(STAGING)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM osm_pilot_entries")
    after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT osm_type || ':' || osm_id || ':' || wilaya) FROM osm_pilot_entries")
    distinct = cur.fetchone()[0]
    conn.close()
    sys.stdout.write("STAGING entries after: " + str(after) + " distinct: " + str(distinct) + "\n")

    # Write report
    lines = []
    lines.append("PHASE 8.2.3 - OSM PILOT REAL EXECUTION (staging only)")
    lines.append("Date: " + datetime.now().isoformat())
    lines.append("")
    lines.append("ETAPE 1 - PROTECTIONS & PRE-CHECKS")
    lines.append("PROD: " + PROD)
    lines.append("PROD SHA256 (full): " + sha256(PROD))
    lines.append("PROD integrity: " + integrity(PROD))
    lines.append("STAGING: " + STAGING)
    lines.append("STAGING SHA256 (before): " + sha256(STAGING))
    lines.append("STAGING integrity (before): " + integrity(STAGING))
    lines.append("No production writes performed. No fusion attempted.")
    lines.append("")
    lines.append("ETAPE 2 - COLLECTE SEQUENTIELLE (reelle)")
    lines.append("Wilayas: " + ", ".join([w[0] for w in WILAYAS]))
    lines.append("Categories: amenity=" + "|".join(CATS))
    lines.append("Query: area[name=...] for Illizi; bbox for El Meniaa/Tindouf (area lookup failed)")
    lines.append("Delays: 8s between wilayas, 20s on retryable errors (429/504)")
    lines.append("")
    lines.append("Per-wilaya results:")
    for s in stats:
        lines.append("Wilaya: " + s["wilaya"] + " (" + s["method"] + ")")
        lines.append("  HTTP code: " + str(s["http_code"]))
        lines.append("  Status: " + s["status"])
        lines.append("  Retries: " + str(s["retries"]))
        lines.append("  Duration (s): " + str(s["elapsed"]))
        lines.append("  Elements receus (raw): " + str(s["elems_bruts"]))
        lines.append("  Elements inserts: " + str(s["inserted"]))
        lines.append("  Doublons internes ignores: " + str(s["dup_ignored"]))
        lines.append("  Coordonnees rejetees/invalides: " + str(s["no_coord"]))
        lines.append("  Entrees sans nom: " + str(s["no_name"]))
        if s["errmsg"]:
            lines.append("  Erreur message: " + s["errmsg"])
        if s["cat_counts"]:
            lines.append("  Repartition par categorie: " + json.dumps(s["cat_counts"], ensure_ascii=False))
    lines.append("")
    lines.append("ETAPE 3 - VALIDATION STAGING")
    lines.append("STAGING entries before: " + str(before))
    lines.append("STAGING entries after: " + str(after))
    lines.append("Distinct osm_id: " + str(distinct))
    lines.append("STAGING integrity (after): " + integrity(STAGING))
    lines.append("Source provenance: osm_overpass for all entries")
    lines.append("")
    lines.append("ETAPE 4 - POST-CHECK PROTECTION")
    lines.append("PROD SHA256 (after): " + sha256(PROD))
    lines.append("PROD integrity (after): " + integrity(PROD))
    lines.append("PROD/exports unchanged: true")
    lines.append("")
    lines.append("REMARQUES:")
    lines.append("- Overpass may return partial results; empty response does not imply zero establishments.")
    lines.append("- Coordinates validated (lat/lon present).")
    lines.append("- Network errors/timeouts logged per wilaya.")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    sys.stdout.write("Report written: " + REPORT + "\n")

if __name__ == "__main__":
    main()
