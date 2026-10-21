# -*- coding: utf-8 -*-
"""Diagnostic minimal de l'arret du scraper."""
import json, sys, os, time, subprocess
from pathlib import Path
import pandas as pd
sys.path.insert(0, r"C:\SANTE_DZ_SCRAPER")
import scraper as S

print("=== PROCESSUS EN COURS ===")
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], capture_output=True, text=True)
print(r.stdout[:500])

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
        print("dernieres lignes (3):")
        for _, r in df.tail(3).iterrows():
            print(" ", r["wilaya"], "|", r[cat_col], "|", str(r.get("nom", ""))[:40])

print()
print("=== progression.json ===")
pj = S.PROGRESS
if pj.exists():
    d = json.loads(pj.read_text(encoding="utf-8"))
    print("version:", d.get("version"))
    print("current:", d.get("current"))
    print("updated_at:", d.get("updated_at"))
    comp = d.get("completed", [])
    print("completed:", len(comp))
    wils = sorted(set(x[0] for x in comp if isinstance(x, list) and len(x) == 2))
    print("wilayas:", wils)

print()
print("=== scraping_progress.json ===")
sp = S.PROGRESS_JSON
if sp.exists():
    d = json.loads(sp.read_text(encoding="utf-8"))
    print("version:", d.get("version"))
    print("timestamp:", d.get("timestamp"))
    print("status:", d.get("status"))
    print("wilaya_en_cours:", d.get("wilaya_en_cours"))
    print("last_request:", d.get("last_request"))
    print("total_national:", d.get("total_national_unique"))
    print("wilayas_terminees:", len(d.get("wilayas_terminees", [])))
    print("wilayas_erreur:", d.get("wilayas_erreur"))

print()
print("=== SCRAPING_NATIONAL_STATUS.xlsx ===")
sx = S.STATUS_XLSX
if sx.exists():
    df = pd.read_excel(sx, dtype=str).fillna("")
    for _, r in df.iterrows():
        if r["statut"] != "NON DÉMARRÉ":
            print(" ", r["wilaya_num"], r["nom_wilaya"], r["statut"], r["total_resultats"])

print()
print("=== XLSX par wilaya ===")
wdir = S.WILAYAS_DIR
if wdir.exists():
    for f in sorted(wdir.glob("*.xlsx")):
        print(" ", f.name, f.stat().st_size, "bytes")

print()
print("=== FICHIERS RECENTS (< 2h) ===")
now = time.time()
for f in S.EXPORTS.glob("*"):
    if f.is_file() and (now - f.stat().st_mtime) < 7200:
        print(" ", f.name, f.stat().st_size, int((now - f.stat().st_mtime) / 60), "min")