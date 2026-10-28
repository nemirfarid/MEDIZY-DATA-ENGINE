#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Client Google Places API (Places Web Service)
================================================================
Support de l'enrichissement via Google Places (Nearby Search, Text Search et Details).
Permet l'intégration de structures avec coordonnées GPS haute précision et place_id.
"""

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .classifier import classify_facility, normalize_algerian_phone

logger = logging.getLogger("medizy.google_places")

GOOGLE_PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


class GooglePlacesClient:
    """Client officiel pour l'API Google Places avec gestion des quotas et pagination."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            logger.warning("Aucune clé GOOGLE_PLACES_API_KEY configurée. Le client sera inopérant sans clé valide.")

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Clé API Google Places requise pour effectuer des requêtes.")

        params["key"] = self.api_key
        query_string = urllib.parse.urlencode(params)
        url = f"{GOOGLE_PLACES_BASE}/{endpoint}/json?{query_string}"

        req = urllib.request.Request(url, headers={"User-Agent": "MedizyIngest/2.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            error_message = data.get("error_message", "Statut inconnu")
            raise RuntimeError(f"Erreur Google Places API [{status}]: {error_message}")

        return data

    def text_search(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None,
        radius_meters: int = 50000,
        wilaya: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Recherche plein texte (ex: 'CHU Alger', 'Polyclinique Oran', 'EPH Béjaïa').
        Gère jusqu'à 3 pages de résultats (max 60 résultats par requête Google).
        """
        params: Dict[str, Any] = {"query": query, "language": "fr", "region": "dz"}
        if location:
            params["location"] = f"{location[0]},{location[1]}"
            params["radius"] = radius_meters

        results: List[Dict[str, Any]] = []
        next_page_token = None

        for page in range(3):
            if next_page_token:
                time.sleep(2.0)  # Délai obligatoire pour l'activation du next_page_token Google
                params = {"pagetoken": next_page_token, "key": self.api_key}

            try:
                data = self._request("textsearch", params)
                for item in data.get("results", []):
                    parsed = self._parse_place_item(item, default_wilaya=wilaya)
                    if parsed:
                        results.append(parsed)

                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break
            except Exception as e:
                logger.error(f"Erreur lors de la pagination text_search '{query}': {e}")
                break

        return results

    def nearby_search(
        self,
        location: Tuple[float, float],
        radius_meters: int = 15000,
        place_type: str = "hospital",
        wilaya: str = "",
    ) -> List[Dict[str, Any]]:
        """Recherche par proximité GPS (Nearby Search) autour d'un centre de wilaya/commune."""
        params = {
            "location": f"{location[0]},{location[1]}",
            "radius": radius_meters,
            "type": place_type,
            "language": "fr",
        }
        data = self._request("nearbysearch", params)
        results = []
        for item in data.get("results", []):
            parsed = self._parse_place_item(item, default_wilaya=wilaya)
            if parsed:
                results.append(parsed)
        return results

    def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les détails enrichis d'un établissement (téléphone, horaires, site web)."""
        params = {
            "place_id": place_id,
            "fields": "name,formatted_phone_number,international_phone_number,formatted_address,geometry,opening_hours,website,rating,user_ratings_total,types",
            "language": "fr",
        }
        try:
            data = self._request("details", params)
            return data.get("result")
        except Exception as e:
            logger.error(f"Échec de récupération des détails pour place_id {place_id}: {e}")
            return None

    def _parse_place_item(self, item: Dict[str, Any], default_wilaya: str = "") -> Optional[Dict[str, Any]]:
        name = item.get("name")
        geometry = item.get("geometry", {}).get("location", {})
        lat = geometry.get("lat")
        lon = geometry.get("lng")
        place_id = item.get("place_id")

        if not name or lat is None or lon is None or not place_id:
            return None

        # Bornes Algérie
        if not (18.0 <= lat <= 38.5 and -9.5 <= lon <= 13.0):
            return None

        types = item.get("types", [])
        facility_type = classify_facility(name=name, google_types=types)

        raw_phone = item.get("formatted_phone_number") or item.get("international_phone_number")
        phone_e164, phone_disp = normalize_algerian_phone(raw_phone)

        address = item.get("formatted_address", "")

        return {
            "name": name.strip(),
            "type": facility_type,
            "wilaya": default_wilaya,
            "commune": "",
            "address": address.strip(),
            "phone": phone_disp or raw_phone or "",
            "phone_normalized": phone_e164,
            "latitude": float(lat),
            "longitude": float(lon),
            "source": "google_places",
            "google_place_id": place_id,
            "osm_id": None,
            "is_claimed": False,
            "is_verified": False,
            "metadata": {
                "google_rating": item.get("rating"),
                "google_user_ratings_total": item.get("user_ratings_total"),
                "google_types": types,
            },
        }
