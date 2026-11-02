#!/usr/bin/env python3
"""Live Google Places API (New) lookup for MEDIZY.

Google Places content is shown only in the current terminal session.
Only Google Place IDs may be persisted by this tool. Do not save names,
addresses, phone numbers, ratings, coordinates, reviews, or other Places
content into MEDIZY/CSV/SQLite unless Google's current contract explicitly
permits that use.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.types",
    "places.location",
    "places.googleMapsUri",
    "nextPageToken",
])

DEFAULT_QUERIES = [
    "pharmacie", "médecin", "cabinet médical", "clinique",
    "laboratoire d'analyses médicales", "dentiste",
    "centre d'imagerie médicale", "centre de santé",
]

def request_page(api_key: str, query: str, page_token: str | None = None) -> dict:
    body = {"textQuery": query, "languageCode": "fr", "regionCode": "DZ"}
    if page_token:
        body["pageToken"] = page_token
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Places API HTTP {exc.code}: {detail}") from exc

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recherche live d'établissements de santé via Google Places API."
    )
    parser.add_argument("--query", action="append", help="Recherche; répétable.")
    parser.add_argument("--wilaya", default="Algérie", help="Zone à ajouter à chaque recherche.")
    parser.add_argument("--max-pages", type=int, default=3, choices=range(1, 4))
    parser.add_argument("--save-place-ids", help="CSV facultatif contenant uniquement les place_id.")
    args = parser.parse_args()

    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        print("ERREUR: définissez GOOGLE_MAPS_API_KEY dans votre environnement.", file=sys.stderr)
        return 2

    queries = args.query or DEFAULT_QUERIES
    seen_ids: set[str] = set()
    rows: list[dict] = []
    count = 0

    for term in queries:
        query = f"{term} en {args.wilaya}"
        token = None
        for page in range(args.max_pages):
            data = request_page(key, query, token)
            places = data.get("places", [])
            for place in places:
                pid = place.get("id")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                count += 1
                # Details are printed live for user inspection, not persisted.
                live = {
                    "google_place_id": pid,
                    "name": (place.get("displayName") or {}).get("text"),
                    "address": place.get("formattedAddress"),
                    "phone": place.get("nationalPhoneNumber"),
                    "website": place.get("websiteUri"),
                    "types": place.get("types", []),
                    "location": place.get("location"),
                    "google_maps_url": place.get("googleMapsUri"),
                }
                print(json.dumps(live, ensure_ascii=False))
                rows.append({"place_id": pid})
            token = data.get("nextPageToken")
            if not token:
                break
            time.sleep(2)

    if args.save_place_ids:
        output = Path(args.save_place_ids)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["place_id"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Place IDs enregistrés: {output} ({len(rows)} identifiants)", file=sys.stderr)

    print(
        f"\nRecherche terminée: {count} identifiants uniques observés. "
        "Les détails affichés proviennent de Google Maps et ne sont pas enregistrés.",
        file=sys.stderr,
    )
    print("Attribution: données fournies par Google Maps Platform.", file=sys.stderr)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError) as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        raise SystemExit(1)
