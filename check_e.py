# -*- coding: utf-8 -*-
"""Check state of D:\SANTE_DZ_EXPORTS."""
import json, sys, time, subprocess
from pathlib import Path
import pandas as pd
sys.path.insert(0, "C:\SANTE_DZ_SCRAPER")
import scraper as S

EXPORTS = Path(r"D:\SANTE_DZ_EXPORTS")
print("=== D:\SANTE_DZ_EXPORTS existe ? ===", EXPORTS.exists())

if EXPORTS.exists():
    print()
    print("=== FICHIERS ===")
    for f in sorted(EXPORTS.glob("*")):
        if f.is_file():
            print(" ", f.name, f.stat().st_size, "bytes")

    print()
    print("=== checkpoint.csv ===")
    cp = EXPORTS / "checkpoint.csv"
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
    print("=== progression.json ===")
    pj = EXPORTS / "progression.json"
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
    sp = EXPORTS / "scraping_progress.json"
    if sp.exists():
        d = json.loads(sp.read_text(encoding="utf-8"))
        print("version:", d.get("version"))
        print("timestamp:", d.get("timestamp"))
        print("status:", d.get("status"))
        print("wilaya_en_cours:", d.get("wilaya_en_cours"))
        print("total_national:", d.get("total_national_unique"))
        print("wilayas_terminees:", len(d.get("wilayas_terminees", [])))

    print()
    print("=== XLSX par wilaya ===")
    wdir = EXPORTS / "wilayas"
    if wdir.exists():
        for f in sorted(wdir.glob("*.xlsx")):
            print(" ", f.name, f.stat().st_size, "bytes")

print()
print("=== PROCESSUS python.exe ===")
r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], capture_output=True, text=True)
print(r.stdout[:600])
