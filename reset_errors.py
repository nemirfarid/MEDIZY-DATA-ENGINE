@# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
sys.path.insert(0, "C:\SANTE_DZ_SCRAPER")
import scraper as S

error_wilayas = ["Béchar", "Bouira", "Tamanrasset", "Tiaret", "Tizi Ouzou"]
for w in error_wilayas:
    p = S.wilaya_export_path(w)
    if p.exists():
        p.unlink()
        print("[CLEAN] Supprime", p.name)

sp = S.PROGRESS_JSON
if sp.exists():
    d = json.loads(sp.read_text(encoding="utf-8"))
    d["wilayas_erreur"] = []
    d["wilaya_en_cours"] = None
    d["status"] = "EN COURS"
    S.atomic_write_json(sp, d)

pj = S.PROGRESS
if pj.exists():
    d = json.loads(pj.read_text(encoding="utf-8"))
    d["completed"] = [x for x in d.get("completed", []) if x[0] not in error_wilayas]
    d["current"] = None
    S.atomic_write_json(pj, d)
    print("progression.json:", len(d["completed"]), "entrees")

print("Termine")
