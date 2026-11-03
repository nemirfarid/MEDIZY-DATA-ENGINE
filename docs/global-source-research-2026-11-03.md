# MEDIZY — Global healthcare/POI source research (2026-11-03)

## Objective and safety
Reach more than 45,000 genuinely distinct, verifiable healthcare facilities in Algeria. The historical 41,423 figure is a reference only; verify the live production database independently before stating the current baseline. Never write to or reset production. All collection is isolated staging. Do not count pharmacies/practitioners as facilities unless the MEDIZY taxonomy explicitly includes them as separately reported classes. Preserve source, source ID, license, source release/date, original category, raw record and retrieval provenance.

## Highest-priority downloadable/open sources

### 1. Overture Maps — Places
- Official guide: https://docs.overturemaps.org/guides/places/
- Download/access guide: https://docs.overturemaps.org/
- Public GeoParquet releases on S3/Azure; filter the Algeria bbox/country division and Health Care taxonomy locally with DuckDB.
- Official documentation describes tens of millions of POIs and the Health Care top-level taxonomy. Place theme licenses are source-dependent (including CDLA Permissive 2.0, Apache 2.0 and CC0); retain provider and license provenance. It explicitly says the Places theme does not contain OSM data.
- This is a bulk data source, not a geocoding API. Download only the relevant partitions/columns where possible.

### 2. Foursquare Open Source Places
- Access: https://docs.foursquare.com/data-products/docs/access-fsq-os-places
- Schema: https://docs.foursquare.com/data-products/docs/places-os-data-schema
- Free open dataset under Apache 2.0; current access pattern is Places Portal + account + access token + Iceberg catalog (not the old public S3 workflow).
- Schema includes fsq_place_id, name, WGS84 lat/lon, address, tel, website, email, category IDs/labels and social links when present.
- Verify Algeria coverage empirically after access; global headline counts are not evidence of Algeria coverage.

### 3. Healthsites.io / Global Healthsites Mapping Project
- Data download/map: https://healthsites.io/how-to-gather
- Map/project: https://maps.healthsites.io/
- OSM Wiki extraction notes: https://wiki.openstreetmap.org/wiki/Global_Healthsites_Mapping_Project
- Healthcare-specific dataset; download the global archive or Algeria country extract and inspect country coverage before assuming it adds records.
- Data license is ODbL; comply with attribution/share-alike obligations. Keep this source separately attributable from OSM because its data may overlap with OSM.

### 4. Humanitarian Data Exchange (HDX) / HOT
- Portal: https://data.humdata.org/
- Search for HOT / Global Healthsites Mapping Project / Algeria health facilities. GeoJSON, CSV or shapefile exports may be available.
- Treat country extracts as dated snapshots. Confirm dataset page, exact license, last update and whether records are derived from OSM before ingesting.

### 5. Existing sources to retain
- Geofabrik Algeria OSM PBF: https://download.geofabrik.de/africa/algeria.html
- OSM is ODbL. Process nodes, ways and relations/areas where feasible; avoid veterinary and generic social-facility contamination. Keep pharmacies, individual practices and facilities as distinct taxonomy classes.
- GeoAlgeria/HOT exports already in this repository history must be independently revalidated and deduplicated, not blindly counted.
- Wikidata is supplementary only; category errors and sparse contact fields were observed in the prior extract.

## APIs / secondary verification sources (not primary bulk sources)

### Geoapify Places
- Docs: https://apidocs.geoapify.com/docs/places/
- Official free allowance shown: 3,000 credits/day; no credit card. A credit is charged per 20 returned places, so this is a request/credit allowance, not a promise of exhaustive national extraction.
- API key required. Useful for small, targeted validation samples by wilaya/category, subject to terms. Do not use as a bulk mirror or assume API results can be permanently redistributed without checking current terms.

### TomTom Search / Places
- Docs: https://docs.tomtom.com/search-api/documentation/product-information/introduction
- Pricing: https://docs.tomtom.com/pricing
- Current pricing page shows limited free Search/Geocoding quotas; Points of Interest API is listed as contact-sales. Use only for spot checks after confirming Algeria POI coverage and storage rights. Not a bulk open dataset.

### Esri ArcGIS Places
- Docs: https://developers.arcgis.com/rest/places/
- Pricing: https://developers.arcgis.com/pricing/
- Limited free Places search/attribute quotas, then paid. Can be used for carefully scoped validation samples; not a free nationwide bulk dataset. Verify service data coverage and retention terms.

### Mapbox Search Box
- Docs: https://docs.mapbox.com/api/search/search-box/
- Pricing: https://www.mapbox.com/pricing
- Limited free quota for some search endpoints. Official documentation says Search Box results cannot be stored. Therefore do not ingest its results into MEDIZY; at most use for ephemeral user-facing search if compliant.

### HERE
- Coverage table: https://docs.here.com/geocoding-and-search/docs/search-local-coverage
- Algeria is marked “Untested” in the local coverage table (French supported; Arabic not supported). Do not assume completeness. Test only if a no-cost account/quota and retention terms are confirmed.

### Apple Maps
- Server API: https://developer.apple.com/documentation/applemapsserverapi
- Requires Apple developer identifier/private key/JWT setup; the stated service-call quota is not a bulk data download grant. Not prioritized.

### Baidu / Tencent / AMAP (China)
- Baidu: https://lbsyun.baidu.com/
- Tencent: https://lbs.qq.com/
- AMAP overseas platform: https://mapsplatform.opnavi.com/
- Strong China-centric POI products; no verified evidence in this research that they provide comprehensive Algeria health POI data under a free bulk-download license. Only consider a small manual coverage test; do not build a core ingestion dependency.

## Other global providers considered
- Google Maps Platform: not a downloadable open POI dataset; billing/account constraints and restrictive storage terms make it unsuitable for building a persistent independent directory.
- Yandex / 2GIS / Naver / Kakao: no verified free, licensed, comprehensive Algeria bulk health-facility feed found in this review. Do not treat their consumer map coverage as permission to scrape.
- Meta POI contribution is available through Overture, so use the Overture distribution rather than attempting to scrape consumer Facebook/Instagram maps.
- OpenBuildingMap / Google Open Buildings / Microsoft building footprints are building geometry, not healthcare POI inventories; not a primary source for facility counts.

## Required execution sequence
1. Download Overture Places release; locally filter Algeria and relevant health taxonomy. Capture release ID, provider, license and raw source fields.
2. Obtain Foursquare Open Source Places portal access; filter Algeria and health categories. Preserve Apache 2.0 and provenance metadata.
3. Download Healthsites global/country data and HDX Algeria snapshots; establish overlap with OSM before counting unique records.
4. Re-run OSM extraction with relation/area support and strict healthcare taxonomy; keep practitioner/pharmacy classes separate.
5. Run source-specific QA, then cross-source candidate matching by normalized name + category + spatial distance + phone/address. Matching only creates review candidates; no automatic deletion or production merge.
6. Generate a report by source, wilaya, category, geocoding completeness, contact completeness, exact duplicates, probable duplicates, rejected records and human-review queue.
7. Verify final distinct count against a fresh read-only production export. Only then report progress toward 45,000.

## Acceptance criteria
- “45,000 reached” means at least 45,001 distinct, plausibly real, healthcare entities after cross-source deduplication and quality review—not raw rows, API hits, buildings, branches duplicated across providers, or unsupported categories.
- Never claim target achieved from search result counts or provider global totals.
- Never overwrite production; stage, back up and require explicit human approval for any future import.
- Do not commit downloaded datasets, private exports, database files, API keys or personal data to Git.
