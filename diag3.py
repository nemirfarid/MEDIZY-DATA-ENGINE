# -*- coding: utf-8 -*-
"""Check processus python.exe actuels avec commandes."""
import json, sys, time, subprocess
from pathlib import Path
import pandas as pd
sys.path.insert(0, r"C:\SANTE_DZ_SCRAPER")
import scraper as S

print("=== PROCESSUS python.exe avec commandes ===")
try:
    r = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine,WorkingSetSize,CreationDate", "/format:csv"],
        capture_output=True, text=True, timeout=15
    )
    print(r.stdout[:3000])
except Exception as e:
    print("wmic error:", e)

print()
print("=== PROCESSUS chrome/chromium ===")
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq *chrom*"], capture_output=True, text=True)
print(r.stdout[:600] if r.stdout else "(aucun)")

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
    st = sp.stat()
    print("modifie:", st.st_mtime, "il y a", int((time.time() - st.st_mtime) / 60), "min")
    d = json.loads(sp.read_text(encoding="utf-8"))
    print("version:", d.get("version"))
    print("timestamp:", d.get("timestamp"))
    print("status:", d.get("status"))
    print("wilaya_en_cours:", d.get("wilaya_en_cours"))
    print("last_request:", d.get("last_request"))
    print("total_national:", d.get("total_national_unique"))
    print("wilayas_terminees:", len(d.get("wilayas_terminees", [])))

print()
print("=== Derniers fichiers modifies (< 30 min) ===")
now = time.time()
for f in S.EXPORTS.glob("*"):
    if f.is_file() and (now - f.stat().st_mtime) < 1800:
        print(" ", f.name, f.stat().st_size, int((now - f.stat().st_mtime) / 60), "min")