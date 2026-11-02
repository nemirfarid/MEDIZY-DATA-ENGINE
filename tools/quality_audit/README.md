# MEDIZY staging quality audit

This audit is deliberately read-only. It reads a source CSV and optionally an existing MEDIZY CSV export, then writes a filtered candidate CSV and JSON report. It never connects to or modifies the production database.

## Example

```bash
python tools/quality_audit/audit_staging.py \
  --input data/staging/wikidata_algeria_healthcare.csv \
  --output data/staging/wikidata_audited_candidates.csv \
  --report data/staging/wikidata_quality_report.json
```

For identifier-only comparison with an authorized export of the current MEDIZY dataset:

```bash
python tools/quality_audit/audit_staging.py --input incoming.csv --master medizy_export.csv
```

The master export is read only. Comparison is limited to matching source + identifier fields; it is not fuzzy real-world deduplication. Candidates still require human verification. Automated filtering cannot establish that a place is open, licensed, or currently operating.

## Important
- Never upload patient or private user data to this repository.
- Do not commit the production MEDIZY database.
- Do not merge staging output automatically.
- OSM data is ODbL and requires attribution; Wikidata is CC0.
