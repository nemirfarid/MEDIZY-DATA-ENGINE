# OpenStreetMap Algeria healthcare extractor

No Google API key is required. This workflow downloads the public Geofabrik
Algeria PBF extract and filters mapped health-related OSM objects locally.

## Run on GitHub

Repository → Actions → **Build Algeria healthcare staging extract** →
Run workflow. The CSV is published as a temporary Actions artifact for 14 days;
it is not committed to Git and does not connect to the production MEDIZY DB.

## Run locally

```powershell
python -m pip install -r tools/osm_healthcare/requirements.txt
python tools/osm_healthcare/extract_osm_healthcare.py --download
```

## Scope and limitations

The extractor captures OSM nodes and ways tagged with health-related values:
pharmacies, hospitals, clinics, doctors' practices, dentists, health posts,
laboratories and other `healthcare=*` features. OSM tagging is community
maintained and incomplete; it is not a national licensing register. A way's
coordinates are an approximate average of its nodes, not a surveyed entrance.
Relation-only features and complex polygon geometry need a later geometry pass.

Every row retains its OSM type/id and source URL. Deduplication is by OSM object
identity in this first pass; cross-source and real-world duplicate review remains
a separate stage. Records are marked `needs_verification`.

## Licensing

OpenStreetMap data is licensed under ODbL 1.0. Attribution is required and
database redistribution can trigger share-alike obligations. Review the ODbL
and MEDIZY distribution model before publishing the merged database:
https://www.openstreetmap.org/copyright
https://opendatacommons.org/licenses/odbl/1-0/

Geofabrik Algeria extract:
https://download.geofabrik.de/africa/algeria.html
