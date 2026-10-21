import sqlite3, csv, json, os, glob
from collections import Counter, defaultdict
DB = r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
EXP = r"D:\SANTE_DZ_EXPORTS"
print("="*70)
print("DIAGNOSTIC MEDIZY/SANTE_DZ (read-only)")
print("="*70)

# --- DB ---
print("\n[1] BASE SQLite :", DB)
if os.path.exists(DB):
    print("  taille:", round(os.path.getsize(DB)/1e6,1), "MB  mtime:", os.path.getmtime(DB))
    con = sqlite3.connect("file:"+DB+"?mode=ro", uri=True)
    cur = con.cursor()
    tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    print("  tables:", tabs)
    main = None
    for t in tabs:
        cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t).fetchall()]
        n = cur.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
        print("    %s : %d rows ; cols=%s" % (t, n, cols[:14]))
        if t == main or (main is None and any(c in cols for c in ("nom",)) and any(c in cols for c in ("wilaya",))):
            main = t
    if main:
        mcols = set(c[1] for c in cur.execute("PRAGMA table_info(%s)" % main).fetchall())
        print("\n[2] TABLE PRINCIPALE :", main)
        print("  rows total:", cur.execute("SELECT COUNT(*) FROM %s" % main).fetchone()[0])
        if "wilaya" in mcols:
            print("  wilayas distinctes:", cur.execute("SELECT COUNT(DISTINCT wilaya) FROM %s" % main).fetchone()[0])
        # latest timestamp
        ts_cols = [c for c in ("date_extraction","created_at","updated_at","last_seen","timestamp") if c in mcols]
        if ts_cols:
            print("  derniere date (%s):" % ts_cols[0], cur.execute("SELECT MAX(%s) FROM %s" % (ts_cols[0],main)).fetchone()[0])
        # duplicates sur cle naturelle
        for key in [("nom","wilaya"),("nom","wilaya","adresse"),("nom","telephone")]:
            if all(c in mcols for c in key):
                tot = cur.execute("SELECT COUNT(*) FROM %s" % main).fetchone()[0]
                uniq = cur.execute("SELECT COUNT(DISTINCT %s) FROM %s" % (",".join(key), main)).fetchone()[0]
                print("  dup sur %s: total=%d unique=%d doublons=%d" % (key, tot, uniq, tot-uniq))
        # wilaya counts
        if "wilaya" in mcols:
            top = cur.execute("SELECT wilaya,COUNT(*) FROM %s GROUP BY wilaya ORDER BY COUNT(*) DESC LIMIT 4" % main).fetchall()
            print("  top wilayas:", top)
        # categories present?
        for c in ("categorie","category","specialite","type_entite"):
            if c in mcols:
                cats = cur.execute("SELECT COUNT(DISTINCT %s) FROM %s" % (c, main)).fetchone()[0]
                print("  categories distinctes (%s):" % c, cats); break
    con.close()
else:
    print("  -> DB absente (le chemin tools/scraping/data/sante_dz_real.db n'existe pas).")

# --- exports ---
print("\n[3] DOSSIER EXPORTS :", EXP, "exists:", os.path.isdir(EXP))
cp = os.path.join(EXP, "checkpoint.csv")
if os.path.exists(cp):
    with open(cp, encoding="utf-8-sig") as f:
        r = csv.reader(f); hdr = next(r); rows = sum(1 for _ in r)
    print("  checkpoint.csv: %d lignes, cols=%s" % (rows, hdr))
else:
    print("  checkpoint.csv absent")
for jf in ("progression.json","scraping_progress.json"):
    j = os.path.join(EXP, jf)
    if os.path.exists(j):
        d = json.load(open(j, encoding="utf-8"))
        if jf=="progression.json":
            comp = d.get("completed",[])
            print("  %s: paires=%d current=%s" % (jf, len(comp), d.get("current")))
        else:
            print("  %s: wilayas_terminees=%s/58 status=%s" % (jf, len(d.get("wilayas_terminees",[])), d.get("status")))
    else:
        print("  %s absent" % jf)
xls = glob.glob(EXP + "/*.xlsx") + glob.glob(EXP + "/**/*.xlsx", recursive=True)
print("  xlsx total:", len(xls))
