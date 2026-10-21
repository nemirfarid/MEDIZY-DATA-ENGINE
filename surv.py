# -*- coding: utf-8 -*-
"""Surveillance scraper PID 14108 - check specifique PID + ligne commande."""
import json, sys, time, subprocess, os
from pathlib import Path
import pandas as pd
sys.path.insert(0, r"C:\SANTE_DZ_SCRAPER")
import scraper as S

print("=== SURVEILLANCE ===")
print("Heure:", time.strftime("%H:%M:%S"))

# Check PID 14108 specifiquement
print()
print("=== PID 14108 (check specifique) ===")
try:
    r = subprocess.run(
        ["wmic", "process", "where", "processid=14108", "get", "processid,commandline,workingsetsize"],
        capture_output=True, text=True, timeout=15
    )
    out = r.stdout.strip()
    print(out if out else "PID 14108 N'EXISTE PAS")
except Exception as e:
    print("err:", e)

# List all python with cmdline
print()
print("=== Tous les python.exe avec commande ===")
try:
    r = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "processid,commandline,workingsetsize"],
        capture_output=True, text=True, timeout=15
    )
    print(r.stdout[:1500] if r.stdout else "(aucun)")
except Exception as e:
    print("err:", e)

print()
print("=== checkpoint.csv ===")
cp = S.CHECKPOINT
if cp.exists():
    st = cp.stat()
    print("modifie:", st.st_mtime, "il y a", int((time.time() - st.st_mtime) / 60), "min")
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
print("=== progression.json ===")
pj = S.PROGRESS
if pj.exists():
    st = pj.stat()
    print("modifie:", st.st_mtime, "il y a", int((time.time() - st.st_mtime) / 60), "min")
    d = json.loads(pj.read_text(encoding="utf-8"))
    print("version:", d.get("version"), "| current:", d.get("current"), "| updated_at:", d.get("updated_at"), "| completed:", d.get("completed"))

print()
print("=== scraping_progress.json ===")
sp = S.PROGRESS_JSON
if sp.exists():
    st = sp.stat()
    print("modifie:", st.st_mtime, "il y a", int((time.time() - st.st_mtime) / 60), "min")
    d = json.loads(sp.read_text(encoding="utf-8"))
    print("version:", d.get("version"), "| status:", d.get("status"), "| wilaya_en_cours:", d.get("wilaya_en_cours"))
    print("timestamp:", d.get("timestamp"), "| last_request:", d.get("last_request"))
    print("total_national:", d.get("total_national_unique"), "| wilayas_terminees:", len(d.get("wilayas_terminees", [])))

print()
print("=== XLSX par wilaya ===")
wdir = S.WILAYAS_DIR
if wdir.exists():
    for f in sorted(wdir.glob("*.xlsx")):
        print(" ", f.name, f.stat().st_size, "bytes")

print()
print("=== Derniers fichiers modifies (< 30 min) ===")
now = time.time()
found = False
for f in S.EXPORTS.glob("*"):
    if f.is_file() and (now - f.stat().st_mtime) < 1800:
        print(" ", f.name, f.stat().st_size, int((now - f.stat().st_mtime) / 60), "min")
        found = True
if not found:
    print("(aucun)")