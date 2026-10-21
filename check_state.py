# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, r"C:\SANTE_DZ_SCRAPER")
import scraper as S

print("=== checkpoint.csv ===")
cp = S.CHECKPOINT
if cp.exists():
    df = pd.read_csv(cp, dtype=str).fillna("")
    print(f"lignes: {len(df)}")
    print(f"wilayas: {sorted(df['wilaya'].unique().tolist())}")

print("\n=== progression.json ===")
pj = S.PROGRESS
if pj.exists():
    d = json.loads(pj.read_text(encoding="utf-8"))
    print(f"version: {d.get('version')}")
    print(f"current: {d.get('current')}")
    comp = d.get("completed", [])
    print(f"completed: {len(comp)}")
    wils = sorted(set(x[0] for x in comp if isinstance(x, list) and len(x) == 2))
    print(f"wilayas: {wils}")

print("\n=== scraping_progress.json ===")
sp = S.PROGRESS_JSON
if sp.exists():
    d = json.loads(sp.read_text(encoding="utf-8"))
    print(json.dumps(d, ensure_ascii=False, indent=2))

print("\n=== SCRAPING_NATIONAL_STATUS.xlsx ===")
sx = S.STATUS_XLSX
if sx.exists():
    df = pd.read_excel(sx, dtype=str).fillna("")
    print(df[["wilaya_num", "nom_wilaya", "statut", "total_resultats"]].to_string(index=False))

print("\n=== XLSX par wilaya ===")
wdir = S.WILAYAS_DIR
if wdir.exists():
    for f in sorted(wdir.glob("*.xlsx")):
        print(f"  {f.name}  {f.stat().st_size} bytes")