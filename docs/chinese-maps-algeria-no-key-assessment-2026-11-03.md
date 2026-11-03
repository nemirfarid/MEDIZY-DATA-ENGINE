# MEDIZY — Chinese map providers: no-key coverage assessment

**Date:** 2026-11-03
**Scope:** Algeria healthcare POIs; Baidu Maps, Amap/Gaode, Tencent Maps
**Mode:** public documentation and web-indexed discovery only; no account, API key, scraping, browser automation, or data harvesting.

## Executive result

No defensible nationwide Algeria healthcare-coverage count can be established from the three Chinese map providers without authorized API access or a provider-approved data sample. Public web search did not produce a reproducible, attributable list of Algerian healthcare POIs from these providers. This is **not proof that their consumer maps contain no Algerian POIs**; it means coverage remains unverified.

| Provider | Official API / overseas access | Can we build MEDIZY staging from results? | Current verdict |
|---|---|---|---|
| Baidu Maps | Place Web Service exists and requires a developer key. Official terms restrict unauthorized extraction and direct storage/use of internal data. | No, not without explicit rights covering external storage and database construction. | Not tested; no key |
| Amap / Gaode | Global Maps Web Service is premium; requires developer account, API key, and overseas permission request. | No. Terms prohibit scraping, copying, caching, storing POI content outside the service and derivative-dataset creation without written permission. | Not tested; no key; written permission needed |
| Tencent Maps | Official developer access and POI search need account/key and quota. Public evidence reviewed did not establish Algeria coverage or an authorized bulk-data license. | No, until the provider confirms coverage and written storage/redistribution rights. | Not tested; no key; coverage unknown |

## Official references reviewed

- Baidu Maps Web Service API: https://api.map.baidu.com/lbsapi/webservice.htm
- Baidu Maps Open Platform terms: https://lbsyun.baidu.com/docs/pcsa?title=law%2Fopen%2Flaw
- Amap Global Maps Web Service overview: https://developer.amap.com/api/web-service/overview
- Amap international Places guide: https://developer.amap.com/api/web-service/guide/searchs
- Amap terms: https://lbs.amap.com/api/policies/terms
- Tencent Maps developer portal: https://lbs.qq.com/

Key points:
- Baidu's API page describes Place search and a key-based service. Its terms limit use to documented API functionality and prohibit unauthorized scraping or extraction. A free quota for eligible non-commercial API use is not a bulk-data license.
- Amap's global Web Service is premium, requires a key and overseas access approval. Its terms prohibit scraping, bulk copying, storing POI content outside the service, and creating derivative datasets absent written permission. The terms also require users outside mainland China / serving overseas users to notify Amap and obtain its decision.
- No official Tencent source reviewed established a free, no-key, Algeria-wide POI feed or rights to persist POI responses in an external directory.

## Safe no-key test performed

1. Reviewed official API documentation and provider terms.
2. Ran public web-indexed searches for Algeria hospitals, clinics and pharmacies associated with Baidu, Amap and Tencent.
3. Found no reproducible provider-attributed Algerian healthcare POI dataset or count.
4. Did not automate consumer-map pages, bypass login/CAPTCHA, inspect private endpoints, or save map results.

**Result:** provider coverage status = UNKNOWN / NOT VERIFIED, not zero.

## Written permission request needed

Before any API test that persists results, request written answers to:
1. Does the service cover Algeria (all 58 wilayas / current administrative boundaries), and what is the POI freshness?
2. Can an Algeria-only pilot be run from outside mainland China?
3. May MEDIZY store POI name, category, address, coordinates, telephone, provider POI ID and source timestamp in its own database?
4. May MEDIZY deduplicate and enrich these records with OSM / Overture / government sources?
5. May MEDIZY retain records after API subscription ends and display them in a third-party app?
6. What attribution, refresh, rate, quota, and commercial-use fees apply?
7. Can the provider supply an authorized bulk export or written dataset license instead of API-only display rights?

## Suggested first pilot (only after written authorization)

- Test localities: Algiers, Oran, Constantine, Mostaganem, Sidi Ali.
- Categories: hospitals, clinics, medical practices, dental practices, pharmacies, laboratories, health centres.
- Record only fields explicitly licensed by the provider.
- Compare against the MEDIZY staging corpus using source IDs and conservative name/address/distance matching.
- Keep provider records in a separate staging namespace. Do not merge into production until licensing, source attribution, and human review pass.

## MEDIZY data-protection rules

- Do not scrape consumer map websites or reverse-engineer private endpoints.
- Do not bypass CAPTCHA, login, rate limits, geographic restrictions, or other controls.
- Do not treat a search result count as a facility count.
- Do not import map-provider POIs into production without explicit storage and derivative-dataset permission.
- Do not overwrite or reset the existing MEDIZY database.
- Keep Overture / OSM / Healthsites extracts separate and preserve per-record provenance and license.

## Decision

**Do not spend time on no-key scraping.** There is no compliant, reproducible path to a nationwide extract from these providers without authorization. Continue the open-data pipeline (Overture, OSM, Healthsites, government sources) while seeking written permission for a small provider pilot.