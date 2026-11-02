# MEDIZY DATA ENGINE

Independent, provenance-first ingestion and quality-control pipeline for healthcare facility records in Algeria.

## Safety rules

- This repository is separate from the MEDIZY production database and never connects to or modifies it.
- All imports go to an isolated SQLite staging database.
- Source labels and source IDs are retained for traceability.
- Duplicate detection produces review candidates; it never deletes records automatically.
- Never commit real facility datasets, personal information, API keys, local databases, or exports. Keep them outside Git.
- Verify source terms, licensing, freshness, and permitted reuse before ingestion or redistribution.
- Counts must be reported as observed, source-attributed records; never inflate totals with duplicates or unverifiable entries.

## Initial capabilities

- Conservative Unicode, phone, and location-field normalization.
- Strong-match duplicate candidate detection.
- Idempotent CSV ingestion into a separate SQLite staging store.
- Tests for normalization, duplicate matching, and staging idempotency.

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

## CSV ingestion

Expected columns can include: `source_id,name,category,wilaya,address,phone,latitude,longitude`.

```bash
medizy ingest-csv --source osm --input path/to/source.csv --db data/staging/medizy_staging.sqlite
```

## Roadmap

1. Source adapters with attribution and licensing metadata.
2. Streaming imports and scalable spatial duplicate candidate generation.
3. Wilaya/category coverage and data-quality reports.
4. Human-reviewed merge/export workflow.
5. Explicit, backed-up, separately approved integration with MEDIZY.

The initial target is to exceed 45,000 genuinely distinct, verifiable facilities. The previously reported 41,423 is a reference figure only; the live MEDIZY database must be independently checked before making a current count claim.
