import sqlite3
import pandas as pd
import json
from pathlib import Path

EXPORTS = Path(r"D:\SANTE_DZ_EXPORTS")

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
conn.row_factory = sqlite3.Row

# Load all places
print("Loading places from database...")
df = pd.read_sql_query("SELECT * FROM places", conn)
print(f"Total rows: {len(df)}")

# Load reference tables
wilayas_df = pd.read_sql_query("SELECT * FROM wilayas", conn)
communes_df = pd.read_sql_query("SELECT * FROM communes", conn)
categories_df = pd.read_sql_query("SELECT * FROM categories", conn)
data_quality_df = pd.read_sql_query("SELECT * FROM data_quality", conn)

conn.close()

print(f"Wilayas: {len(wilayas_df)}")
print(f"Communes: {len(communes_df)}")
print(f"Categories: {len(categories_df)}")

# Data quality analysis
print("\n=== DATA QUALITY ===")
total = len(df)
print(f"Total: {total}")

gps_count = df['latitude'].notna().sum()
phone_count = df['telephone'].astype(str).str.strip().ne('').sum()
addr_count = df['adresse'].astype(str).str.strip().ne('').sum()
commune_count = df['commune'].astype(str).str.strip().ne('').sum()
web_count = df['site_web'].astype(str).str.strip().ne('').sum()
rating_count = df['note'].astype(str).str.strip().ne('').sum()
hours_count = df['horaires'].astype(str).str.strip().ne('').sum()
pid_count = df['place_id'].astype(str).str.strip().ne('').sum()
wilaya_count = df['wilaya'].astype(str).str.strip().ne('').sum()
unique_wilayas = df['wilaya'].dropna().unique()
cat_counts = df['categorie_recherche'].value_counts()

print(f"GPS: {gps_count} / {total} ({100*gps_count/total:.1f}%)")
print(f"Phone: {phone_count} / {total} ({100*phone_count/total:.1f}%)")
print(f"Address: {addr_count} / {total} ({100*addr_count/total:.1f}%)")
print(f"Commune: {commune_count} / {total} ({100*commune_count/total:.1f}%)")
print(f"Website: {web_count} / {total} ({100*web_count/total:.1f}%)")
print(f"Rating: {rating_count} / {total} ({100*rating_count/total:.1f}%)")
print(f"Hours: {hours_count} / {total} ({100*hours_count/total:.1f}%)")
print(f"Place ID: {pid_count} / {total} ({100*pid_count/total:.1f}%)")
print(f"Wilaya: {wilaya_count} / {total} ({100*wilaya_count/total:.1f}%)")
print(f"Unique wilayas: {len(unique_wilayas)}")
print(f"Categories: {len(cat_counts)}")

# --- Export 1: Full national dataset (cleaned) ---
print("\n=== EXPORTING NATIONAL DATASET ===")
export_cols = [
    'id', 'place_id', 'nom', 'adresse', 'telephone', 'site_web', 'note', 'nombre_avis',
    'horaires', 'latitude', 'longitude', 'google_maps_url', 'type_google',
    'wilaya', 'commune', 'categorie_recherche', 'source', 'scrape_date',
    'status', 'created_at', 'updated_at', 'name_status', 'name_source',
    'recovery_date', 'commune_source', 'commune_confidence', 'commune_updated_at'
]

for c in export_cols:
    if c not in df.columns:
        df[c] = ""

df_export = df[export_cols].copy()
df_export = df_export.sort_values(['wilaya', 'commune', 'categorie_recherche', 'nom'], na_position='last')

# Save as CSV
csv_path = EXPORTS / "SANTE_DZ_NATIONAL_FINAL.csv"
df_export.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"CSV: {csv_path} ({len(df_export)} rows)")

# Save as Excel with multiple sheets
xlsx_path = EXPORTS / "SANTE_DZ_NATIONAL_FINAL.xlsx"
with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
    df_export.to_excel(writer, index=False, sheet_name="National")
    
    gps_df = df_export[df_export['latitude'].notna() & df_export['longitude'].notna()]
    gps_df.to_excel(writer, index=False, sheet_name="GPS_presents")
    
    phone_df = df_export[df_export['telephone'].astype(str).str.strip().ne('')]
    phone_df.to_excel(writer, index=False, sheet_name="Avec_telephone")
    
    no_phone_df = df_export[df_export['telephone'].astype(str).str.strip().eq('')]
    no_phone_df.to_excel(writer, index=False, sheet_name="Sans_telephone")
    
    commune_df = df_export[df_export['commune'].astype(str).str.strip().ne('')]
    commune_df.to_excel(writer, index=False, sheet_name="Avec_commune")
    
    # Statistics by wilaya
    stats_wilaya = df_export.groupby('wilaya', dropna=False).agg(
        total=('nom', 'count'),
        gps=('latitude', lambda s: s.notna().sum()),
        phone=('telephone', lambda s: s.astype(str).str.strip().ne('').sum()),
        commune=('commune', lambda s: s.astype(str).str.strip().ne('').sum()),
        website=('site_web', lambda s: s.astype(str).str.strip().ne('').sum()),
        rating=('note', lambda s: s.astype(str).str.strip().ne('').sum()),
        hours=('horaires', lambda s: s.astype(str).str.strip().ne('').sum()),
        place_id=('place_id', lambda s: s.astype(str).str.strip().ne('').sum()),
    ).reset_index()
    stats_wilaya.to_excel(writer, index=False, sheet_name="Stats_par_wilaya")
    
    # Statistics by category
    stats_cat = df_export.groupby('categorie_recherche', dropna=False).agg(
        total=('nom', 'count'),
        gps=('latitude', lambda s: s.notna().sum()),
        phone=('telephone', lambda s: s.astype(str).str.strip().ne('').sum()),
    ).reset_index().sort_values('total', ascending=False)
    stats_cat.to_excel(writer, index=False, sheet_name="Stats_par_categorie")
    
    # Reference tables
    wilayas_df.to_excel(writer, index=False, sheet_name="Wilayas")
    communes_df.to_excel(writer, index=False, sheet_name="Communes")
    categories_df.to_excel(writer, index=False, sheet_name="Categories")
    data_quality_df.to_excel(writer, index=False, sheet_name="Data_Quality_History")

print(f"Excel: {xlsx_path}")

# --- Export 2: Summary report ---
print("\n=== GENERATING SUMMARY REPORT ===")
report = {
    "generated_at": pd.Timestamp.now().isoformat(),
    "total_entries": int(total),
    "wilayas_covered": int(len(unique_wilayas)),
    "categories_covered": int(len(cat_counts)),
    "coverage": {
        "gps_pct": round(100 * gps_count / total, 1),
        "phone_pct": round(100 * phone_count / total, 1),
        "address_pct": round(100 * addr_count / total, 1),
        "commune_pct": round(100 * commune_count / total, 1),
        "website_pct": round(100 * web_count / total, 1),
        "rating_pct": round(100 * rating_count / total, 1),
        "hours_pct": round(100 * hours_count / total, 1),
        "place_id_pct": round(100 * pid_count / total, 1),
    },
    "wilaya_stats": stats_wilaya.to_dict('records'),
    "category_stats": stats_cat.to_dict('records'),
}

report_path = EXPORTS / "SANTE_DZ_FINAL_REPORT.json"
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"Report: {report_path}")

# --- Export 3: Markdown summary ---
md_path = EXPORTS / "SANTE_DZ_FINAL_REPORT.md"
with open(md_path, 'w', encoding='utf-8') as f:
    f.write("# SANTÉ DZ - Final Dataset Report\n\n")
    f.write(f"**Generated:** {report['generated_at']}\n\n")
    f.write(f"**Total Entries:** {report['total_entries']:,}\n")
    f.write(f"**Wilayas Covered:** {report['wilayas_covered']}/58\n")
    f.write(f"**Categories Covered:** {report['categories_covered']}\n\n")
    
    f.write("## Field Coverage\n\n")
    for field, pct in report['coverage'].items():
        f.write(f"- **{field.replace('_pct', '').replace('_', ' ').title()}**: {pct}%\n")
    
    f.write("\n## Wilaya Statistics\n\n")
    f.write("| Wilaya | Total | GPS | Phone | Commune | Website | Rating | Hours | Place ID |\n")
    f.write("|--------|-------|-----|-------|---------|---------|--------|-------|----------|\n")
    for w in report['wilaya_stats']:
        f.write(f"| {w['wilaya']} | {w['total']} | {w['gps']} | {w['phone']} | {w['commune']} | {w['website']} | {w['rating']} | {w['hours']} | {w['place_id']} |\n")
    
    f.write("\n## Category Statistics\n\n")
    f.write("| Category | Total | GPS | Phone |\n")
    f.write("|----------|-------|-----|-------|\n")
    for c in report['category_stats']:
        f.write(f"| {c['categorie_recherche']} | {c['total']} | {c['gps']} | {c['phone']} |\n")

print(f"Markdown report: {md_path}")

print("\n=== EXPORT COMPLETE ===")