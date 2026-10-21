# -*- coding: utf-8 -*-
"""Check final et log du scraper."""
import json, sys, time, subprocess
from pathlib import Path
import pandas as pd
sys.path.insert(0, r"C:\SANTE_DZ_SCRAPER")
import scraper as S

print("=== FINAL CHECK ===")
print("Heure:", time.strftime("%H:%M:%S"))

print()
print("=== Processus python.exe ===")
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], capture_output=True, text=True)
print(r.stdout[:800])

print()
print("=== progression.json ===")
pj = S.PROGRESS
if pj.exists():
    d = json.loads(pj.read_text(encoding="utf-8"))
    print("modifie:", pj.stat().st_mtime, "il y a", int((time.time() - pj.stat().st_mtime) / 60), "min")
    print("version:", d.get("version"), "| current:", d.get("current"), "| updated_at:", d.get("updated_at"), "| completed:", d.get("completed"))

print()
print("=== scraping_progress.json ===")
sp = S.PROGRESS_JSON
if sp.exists():
    d = json.loads(sp.read_text(encoding="utf-8"))
    print("modifie:", sp.stat().st_mtime, "il y a", int((time.time() - sp.stat().st_mtime) / 60), "min")
    print("version:", d.get("version"), "| status:", d.get("status"), "| wilaya_en_cours:", d.get("wilaya_en_cours"))
    print("timestamp:", d.get("timestamp"), "| last_request:", d.get("last_request"))
    print("total_national:", d.get("total_national_unique"), "| wilayas_terminees:", len(d.get("wilayas_terminees", [])))
    print("wilayas_erreur:", d.get("wilayas_erreur"))

print()
print("=== checkpoint.csv ===")
cp = S.CHECKPOINT
if cp.exists():
    df = pd.read_csv(cp, dtype=str).fillna("")
    print("lignes:", len(df))
    print("wilayas:", sorted(df["wilaya"].unique().tolist()))
    cat_col = None
    for c in df.columns:
        if "categor" in c.lower():
            cat_col = c
            break
    if cat_col:
        print("dernieres lignes (5):")
        for _, r in df.tail(5).iterrows():
            print(" ", r["wilaya"], "|", r[cat_col], "|", str(r.get("nom", ""))[:40])

print()
print("=== XLSX par wilaya ===")
wdir = S.WILAYAS_DIR
if wdir.exists():
    for f in sorted(wdir.glob("*.xlsx")):
        print(" ", f.name, f.stat().st_size, "bytes")

print()
print("=== SCRAPING_NATIONAL_STATUS.xlsx ===")
xlsx = S.EXPORTS / "SCRAPING_NATIONAL_STATUS.xlsx"
if xlsx.exists():
    print("modifie:", xlsx.stat().st_mtime, "il y a", int((time.time() - xlsx.stat().st_mtime) / 60), "min")