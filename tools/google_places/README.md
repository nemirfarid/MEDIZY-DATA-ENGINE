# Google Places live lookup (MEDIZY)

This adapter performs live searches against the official Google Places API (New).
It is not a Google Maps webpage scraper and does not bypass access controls.

## Important Google data-use restriction

Google Places content is subject to Google Maps Platform terms. This tool prints
place details to the current terminal session only. It can persist **Place IDs
only**. Do not turn the displayed names, addresses, telephone numbers, websites,
coordinates, ratings, reviews, or other Google Places content into a permanent
MEDIZY dataset or CSV unless your current Google agreement expressly authorizes
that exact use. Place IDs are exempt from Places caching restrictions.

Official policy:
https://developers.google.com/maps/documentation/places/web-service/policies

## 1. Configure Google Cloud

1. Open https://console.cloud.google.com/
2. Create/select a project and enable **Places API (New)**.
3. Configure billing and quotas. Google may charge for requests; set a strict
   quota/budget alert and restrict the API key to Places API.
4. Create an API key. Never paste it into GitHub, source code, chat, or commits.

## 2. Install and run locally

Python 3.10+; no third-party package is required.

PowerShell:
```powershell
$env:GOOGLE_MAPS_API_KEY = "YOUR_KEY"
python tools/google_places/google_places_live.py --wilaya "Mostaganem"
```

Search all Algeria (run several wilayas separately for better coverage):
```powershell
python tools/google_places/google_places_live.py --wilaya "Mostaganem" --max-pages 3
python tools/google_places/google_places_live.py --wilaya "Oran" --max-pages 3
```

Custom searches:
```powershell
python tools/google_places/google_places_live.py --wilaya "Alger" --query "pharmacie" --query "médecin généraliste" --query "laboratoire analyses médicales"
```

Persist only stable Place IDs (allowed exception):
```powershell
python tools/google_places/google_places_live.py --wilaya "Mostaganem" --save-place-ids data/google_place_ids_mostaganem.csv
```

The detailed results are printed live as JSON for inspection. The script does
not write those details to disk and does not connect to the MEDIZY production
database. Search results are not exhaustive: Google applies ranking, regional
coverage, page limits, and query-dependent results. Do not interpret result
counts as the total number of practitioners or facilities in Algeria.

## Security and data quality

- Keep the API key in an environment variable or a local secret manager.
- Restrict the key to Places API (New), set quotas and billing alerts.
- Deduplication uses Place IDs only; one real-world place can sometimes have
  multiple IDs, and IDs can change.
- A Google Maps listing is not proof of professional registration or current
  operation. Human verification is required.
- This module is isolated from production and never deletes or overwrites data.
