import sqlite3
import json
from deduplication import DeduplicationEngine, apply_normalization

# Load all places from database
conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM places')
rows = [dict(row) for row in c.fetchall()]
print(f"Loaded {len(rows)} places from database")

conn.close()

# Apply normalization to all rows
print("Applying normalization...")
normalized_rows = [apply_normalization(r) for r in rows]

# Run deduplication
print("Running deduplication...")
engine = DeduplicationEngine(auto_merge_threshold=80)
deduped_rows, stats, candidates = engine.process(normalized_rows)

print("\nDeduplication Stats:")
for k, v in stats.items():
    print(f"  {k}: {v}")

print(f"\nCandidates for manual review: {len(candidates)}")
for i, (existing, candidate, score, niveau, raisons) in enumerate(candidates[:10]):
    print(f"  Candidate {i+1}: score={score}, niveau={niveau}")
    print(f"    Existing: {existing.get('nom', '')[:50]} | {existing.get('telephone', '')}")
    print(f"    Candidate: {candidate.get('nom', '')[:50]} | {candidate.get('telephone', '')}")
    print(f"    Raisons: {raisons}")

# Save deduplication results
with open(r"D:\SANTE_DZ_EXPORTS\deduplication_candidates.json", "w", encoding="utf-8") as f:
    cand_data = []
    for existing, candidate, score, niveau, raisons in candidates:
        cand_data.append({
            "score": score,
            "niveau": niveau,
            "raisons": raisons,
            "existing": {"id": existing.get("id"), "nom": existing.get("nom"), "telephone": existing.get("telephone"), "wilaya": existing.get("wilaya")},
            "candidate": {"id": candidate.get("id"), "nom": candidate.get("nom"), "telephone": candidate.get("telephone"), "wilaya": candidate.get("wilaya")}
        })
    json.dump(cand_data, f, ensure_ascii=False, indent=2)

print("\nDeduplication candidates saved to deduplication_candidates.json")

# Also save deduplicated data as CSV
import pandas as pd
df = pd.DataFrame(deduped_rows)
df.to_csv(r"D:\SANTE_DZ_EXPORTS\places_deduplicated.csv", index=False, encoding="utf-8-sig")
print(f"Deduplicated data saved: {len(df)} rows")