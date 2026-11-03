# MEDIZY — GitHub methods inventory and execution decision

**Date:** 2026-11-03  
**Target:** >45,000 distinct, verifiable Algerian healthcare entities  
**Production safety:** staging only; no production database writes, resets, merges or deletions.

## 1. GitHub projects examined

| Project | Method / useful capability | MEDIZY decision |
|---|---|---|
| https://github.com/sonagara-vashram/google-maps-scraper | Python HTTP scraper; undocumented Google Maps internal endpoints; claims no API key and grid tiling | Code/method study only. README explicitly says it violates Google terms and is educational-only. Do not run bulk extraction or import its output into MEDIZY. |
| https://github.com/gosom/google-maps-scraper | Go-based Google Maps listing scraper | Inspect architecture and output schema only; same platform-terms and persistent-storage issue applies. |
| https://github.com/omkarcloud/google-maps-scraper | Google Maps scraping / enrichment project | Not a lawful open bulk dataset; not selected for MEDIZY ingestion. |
| https://github.com/ozhehkovski/geoleadscraper | Browser extension for Google Maps, Yandex Maps and 2GIS; CSV/XLSX/JSON export | Useful as a manual research aid, not a nationwide unattended ingestion source. Check each provider's terms before use. |
| https://github.com/healthsites/healthsites | Open healthcare facility data platform built on OSM; ODbL data | High-priority licensed source; download country extracts and compare separately with OSM. |
| https://github.com/project-terraforma/places-truth-reconciliation | Attribute-level reconciliation for Overture Places | Study for provenance-aware cross-source reconciliation; never auto-merge production. |
| https://github.com/dbreunig/poi-polloi | POI API based on Overture Places | Useful reference for querying and indexing Overture; not an additional independent source. |
| https://github.com/xtrustinfo/overture-places-ua | Overture extraction with DuckDB | Reuse the DuckDB/GeoParquet extraction pattern for Algeria; do not copy Ukraine-specific filters. |

## 2. Verified public source leads

- Healthsites public pages describe a downloadable global healthcare dataset under ODbL and country extracts; the OSM wiki documents Healthsites, HDX and HOT Export Tool as extract routes. Global total is not Algeria's count.
- A public Hugging Face dataset `electricsheepafrica/africa-health-facilities-algeria` is indexed with approximately 7.47k rows. It appears derived from HDX/OSM and includes OSM IDs, coordinates, healthcare/amenity tags and source timestamps. Treat it as a candidate snapshot, not 7,470 new facilities; it likely overlaps existing OSM/HDX records. Verify the dataset card and license before reuse.
- GeoAlgeria's published package catalogue lists separate health packages for official public facilities, clinics/proximity facilities and pharmacies. These are separate populations and must not be summed blindly or counted as net-new without record-level comparison.
- The previously processed Overture Algeria extract contains 7,137 candidate rows (6,160 excluding unclassified healthcare and health administration). It is staging only; 799 low-confidence rows, no cross-source deduplication and no production comparison were completed.

## 3. Why Google Maps / Yandex / 2GIS scraper repositories are not a production ingestion path

An open-source license on a scraper's code does not grant rights to extract, retain, republish or create a competing database from the map provider's content. The Google scraper README explicitly discloses undocumented internal endpoints and says the method violates Google terms; Google's terms prohibit exporting/extracting/scraping Maps content for use outside the service. A browser extension does not change the provider's content license. No bulk extraction has been run.

## 4. Recommended lawful execution order

1. Healthsites country export / HDX Algeria snapshot: acquire source file, verify ODbL, inspect date and provenance, extract Algeria only.
2. Hugging Face Algeria health-facilities snapshot: validate dataset card/license, download immutable revision, preserve all original fields and OSM IDs.
3. Overture Places: use existing Algeria staging file and extract any remaining categories with exact taxonomy and provider provenance.
4. Foursquare Open Source Places: use official portal and license only if access is available; verify Algeria coverage before any count.
5. Improve OSM extraction: include relations/areas and strict healthcare taxonomy; keep pharmacies, individual practitioners, veterinary and social services separately classified.
6. GeoAlgeria public-health and proximity packages: validate current source snapshot and compare record-by-record.
7. Reconcile candidates using exact source IDs first, then normalized name + category + spatial distance + phone/address. Matching only creates review queues; no automatic production merge.
8. Read a fresh production export read-only and calculate net-new verified records by source, category and wilaya.

## 5. Acceptance criteria for >45,000

- A record must represent a real healthcare facility/entity in Algeria, not a directory, government office, medical supplier, vet, individual staff member or generic map feature.
- Every record must retain source, source ID, retrieval date, license, source URL and original category.
- Same facility across sources must count once; uncertain matches go to manual review.
- Report facilities, pharmacies and individual practitioners separately.
- Automated checks do not equal field verification; expose verification status and last-confirmed date.
- Only a fresh read-only production comparison can establish net-new additions and whether the target has been exceeded.

## 6. Current status

- GitHub repository search and selected README/source inspection completed.
- Google Maps scraper methods identified, but not run for bulk extraction because the examined method uses undocumented endpoints and violates provider terms.
- Healthsites, HDX, Hugging Face, Overture, GeoAlgeria and reconciliation methods prioritized.
- No new source records were imported into production in this assessment.
- Target status remains **NOT VERIFIED** until a fresh production export and source-level reconciliation are available.