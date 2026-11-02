# Wikidata Algeria healthcare collector

This collector queries the public Wikidata Query Service (WDQS) for healthcare
entities located in Algeria. It requires no Google key and no paid API account.

## Run locally
```bash
python tools/wikidata_healthcare/extract_wikidata_healthcare.py
```

## Data handling
- Output is a CSV under `data/staging/`; production MEDIZY is never opened or modified.
- Every row carries its Wikidata QID and source URL.
- Wikidata structured data is CC0; each record remains marked
  `needs_verification`.
- The collector deduplicates only repeated rows for the same QID. It does not
  claim real-world uniqueness across Wikidata, OSM, GeoAlgeria, or MEDIZY.
- Coverage is expected to be incomplete. Missing records must not be interpreted
  as proof that a facility does not exist.

## Limitations
WDQS is a shared public service with rate limits and occasional timeouts. The
query is intentionally bounded to 10,000 result rows and the selected classes;
it is a supplementary discovery source, not a national registry.
