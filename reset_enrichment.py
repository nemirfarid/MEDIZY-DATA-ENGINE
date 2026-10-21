import sqlite3
import pandas as pd

# Load latest checkpoint
main_checkpoint = pd.read_csv(r"D:\SANTE_DZ_EXPORTS\checkpoint.csv", dtype=str).fillna("")
print(f"Main checkpoint: {len(main_checkpoint)} rows")

# Load enrichment checkpoint
enrich_checkpoint = pd.read_csv(r"D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv", dtype=str).fillna("")
print(f"Enrichment checkpoint: {len(enrich_checkpoint)} rows")

# Update enrichment checkpoint with main checkpoint
main_checkpoint.to_csv(r"D:\SANTE_DZ_EXPORTS\checkpoint_enrichment.csv", index=False, encoding="utf-8-sig")
print("Updated enrichment checkpoint with main checkpoint data")

# Also clear progression to re-process
import json
with open(r"D:\SANTE_DZ_EXPORTS\progression_enrichment.json", "w", encoding="utf-8") as f:
    json.dump({"version": 1, "completed": [], "current": None, "updated_at": None}, f)
print("Cleared enrichment progression")