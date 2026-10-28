#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Client Overpass OpenStreetMap (Santé Algérie)
==================================================================
Extrait tous les établissements de santé (hôpitaux, cliniques, polycliniques,
dispensaires, cabinets) sur les 58 wilayas d'Algérie via l'API Overpass OSM.
Gère les bascules multi-serveurs, le rate-limiting et les découpages spatiaux.
"""

import json
import logging
import time
import urllib.parse
from typing import Any, Dict, Generator, List, Optional
import urllib.request
import urllib.error

from .classifier import classify_facility, normalize_algerian_phone

logger = logging.getLogger("medizy.osm")

# Serveurs Overpass avec bascule automatique en cas de charge (miroirs mondiaux complets)
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Tags cibles pour la santé publique et privée
HEALTH_AMENITIES = ["hospital", "clinic", "doctors", "pharmacy", "dentist"]
HEALTHCARE_TAGS = ["hospital", "clinic", "centre", "doctor", "dispensary"]


class OverpassClient:
    """Client Overpass résilient avec retries, rotation de miroirs et parsing géospatial."""

    def __init__(self, timeout: int = 30, user_agent: str = "MedizyHealthIngest/2.0 (contact@medizy.dz)"):
        self.timeout = timeout
        self.user_agent = user_agent
        self.endpoint_idx = 0

    @property
    def endpoint(self) -> str:
        return self._get_active_endpoint()

    def _get_active_endpoint(self) -> str:
        return OVERPASS_ENDPOINTS[self.endpoint_idx % len(OVERPASS_ENDPOINTS)]

    def _rotate_endpoint(self, wilaya: str = "algerie"):
        self.endpoint_idx += 1
        active = self._get_active_endpoint()
        logger.warning(f"Bascule vers le miroir Overpass: {active}")
        try:
            from medizy_pipeline.api.metrics import record_mirror_failover
            record_mirror_failover(wilaya=wilaya, target_mirror=active)
        except Exception:
            pass

    def execute_query(self, query: str, max_retries: int = 3) -> Dict[str, Any]:
        """Exécute une requête QL Overpass avec gestion des erreurs réseau et HTTP 429/504."""
        for attempt in range(max_retries):
            endpoint = self._get_active_endpoint()
            encoded_data = urllib.parse.urlencode({"data": query}).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=encoded_data,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        body = resp.read().decode("utf-8")
                        return json.loads(body)
            except urllib.error.HTTPError as e:
                logger.warning(f"Erreur HTTP {e.code} sur {endpoint} (tentative {attempt + 1}/{max_retries})")
                if e.code in (429, 502, 503, 504):
                    self._rotate_endpoint()
                    time.sleep(3 * (attempt + 1))
                else:
                    raise
            except Exception as e:
                logger.warning(f"Échec réseau ({e}) sur {endpoint} (tentative {attempt + 1}/{max_retries})")
                self._rotate_endpoint()
                time.sleep(3 * (attempt + 1))

        raise RuntimeError(f"Impossible d'exécuter la requête Overpass après {max_retries} tentatives.")

    def build_wilaya_query(self, wilaya_name: str, bbox: Optional[Tuple[float, float, float, float]] = None) -> str:
        """
        Génère une requête Overpass QL optimisée.
        Si une Bounding Box (min_lat, min_lon, max_lat, max_lon) est fournie, l'utilise directement.
        Sinon, utilise le filtre territorial OSM area.
        """
        amenities = "|".join(HEALTH_AMENITIES)
        healthcares = "|".join(HEALTHCARE_TAGS)

        if bbox:
            min_lat, min_lon, max_lat, max_lon = bbox
            spatial_filter = f"({min_lat},{min_lon},{max_lat},{max_lon})"
            return f"""
                [out:json][timeout:{self.timeout}];
                (
                  nwr["amenity"~"^({amenities})$"]{spatial_filter};
                  nwr["healthcare"~"^({healthcares})$"]{spatial_filter};
                  nwr["emergency"="yes"]{spatial_filter};
                );
                out center tags;
            """
        else:
            # Recherche par zone administrative OSM
            escaped_name = wilaya_name.replace("'", "\\'")
            return f"""
                [out:json][timeout:{self.timeout}];
                area["name"="{escaped_name}"]["admin_level"~"^(4|6)$"]->.searchArea;
                (
                  nwr["amenity"~"^({amenities})$"](area.searchArea);
                  nwr["healthcare"~"^({healthcares})$"](area.searchArea);
                  nwr["emergency"="yes"](area.searchArea);
                );
                out center tags;
            """

    def parse_element(self, element: Dict[str, Any], default_wilaya: str = "") -> Optional[Dict[str, Any]]:
        """Parse un élément OSM (node, way, relation) en objet normalisé Facility."""
        tags = element.get("tags", {})
        if not tags:
            return None

        # Priorité aux noms en français, arabe ou nom par défaut
        name = tags.get("name:fr") or tags.get("name") or tags.get("name:ar") or tags.get("official_name")
        if not name or len(name.strip()) < 2:
            return None

        # Extraction des coordonnées (lat/lon directe pour les nœuds, center pour ways/relations)
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            center = element.get("center") or {}
            lat = center.get("lat")
            lon = center.get("lon")

        if lat is None or lon is None:
            return None

        # Validation des bornes géographiques de l'Algérie
        if not (18.0 <= lat <= 38.5 and -9.5 <= lon <= 13.0):
            return None

        # Téléphone et normalisation
        raw_phone = (
            tags.get("phone")
            or tags.get("contact:phone")
            or tags.get("contact:mobile")
            or tags.get("mobile")
        )
        phone_e164, phone_disp = normalize_algerian_phone(raw_phone)

        # Adresse
        street = tags.get("addr:street", "")
        housenumber = tags.get("addr:housenumber", "")
        full_addr = tags.get("addr:full") or f"{housenumber} {street}".strip() or tags.get("address", "")
        commune = tags.get("addr:city") or tags.get("addr:suburb") or ""

        # Typologie
        facility_type = classify_facility(name=name, raw_tags=tags)

        osm_id = f"{element.get('type')}/{element.get('id')}"

        return {
            "name": name.strip(),
            "type": facility_type,
            "wilaya": default_wilaya,
            "commune": commune.strip(),
            "address": full_addr.strip(),
            "phone": phone_disp or raw_phone or "",
            "phone_normalized": phone_e164,
            "latitude": float(lat),
            "longitude": float(lon),
            "source": "openstreetmap",
            "osm_id": osm_id,
            "google_place_id": None,
            "is_claimed": False,
            "is_verified": False,
            "metadata": {
                "osm_tags": tags,
                "operator": tags.get("operator"),
                "emergency": tags.get("emergency"),
                "opening_hours": tags.get("opening_hours"),
                "website": tags.get("website") or tags.get("contact:website"),
            },
        }

    def fetch_wilaya_facilities(
        self, wilaya_name: str, bbox: Optional[Tuple[float, float, float, float]] = None
    ) -> List[Dict[str, Any]]:
        """Récupère et parse tous les établissements de santé pour une wilaya."""
        query = self.build_wilaya_query(wilaya_name=wilaya_name, bbox=bbox)
        logger.info(f"Requête OSM Overpass pour la wilaya : {wilaya_name}...")
        try:
            data = self.execute_query(query)
            elements = data.get("elements", [])
            facilities = []
            for el in elements:
                parsed = self.parse_element(el, default_wilaya=wilaya_name)
                if parsed:
                    facilities.append(parsed)
            logger.info(f"Wilaya {wilaya_name}: {len(facilities)} structures extraites depuis OSM.")
            return facilities
        except Exception as e:
            logger.error(f"Échec de l'ingestion OSM pour {wilaya_name}: {e}")
            return []
