#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
SANTÉ DZ / MEDIZY — COLLECTEUR MULTI-SOURCES NATIONAL & EXPANSION PHASE 6
========================================================================
Collecteur pour l'ensemble du territoire national algérien :
1. Extraction et chargement du flux OpenStreetMap Overpass (ou cache brut local).
2. Filtrage spatial strict aux frontières algériennes (rattachement aux 58 wilayas et 1 541 communes).
3. Normalisation des tags (nom, catégorie contrôlée, téléphone +213 -> 0, site web, GPS).
4. Moteur de déduplication spatiale (< 60m + similarité de nom > 70%) contre la production.
5. Déduplication interne des candidats (nœuds/ways jumeaux).
6. Stockage sécurisé des nouveaux établissements qualifiés dans D:\SANTE_DZ_EXPORTS\medizy_staging_expansion.db.
"""

import os
import sys
import json
import math
import re
import time
import difflib
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Chemin racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from collectors.base_collector import BaseCollector

# ============================================================================
# CONFIGURATION DES CHEMINS (CONFINEMENT DISQUE D:)
# ============================================================================
PROD_DB_PATH = os.environ.get("MEDIZY_DB_PATH") or str(PROJECT_ROOT / "medizy_scraper.db")
COMMUNES_JSON_PATH = str(PROJECT_ROOT / "communes_algerie_officielles.json")
EXPORTS_DIR = Path(r"D:\SANTE_DZ_EXPORTS")
RAW_OSM_CACHE = str(EXPORTS_DIR / "osm_algeria_health_raw.json")
STAGING_DB_PATH = str(EXPORTS_DIR / "medizy_staging_expansion.db")
AUDIT_REPORT_PATH = str(EXPORTS_DIR / "phase6_expansion_audit_report.json")

# Bounding box Algérie
BBOX_ALGERIA = "18.9,-8.7,37.1,12.0"
SOURCE_TAG = "osm_overpass_expansion_2026"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def strip_accents(s: str) -> str:
    """Supprime les accents et normalise la chaîne."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcule la distance géodésique en mètres entre deux points WGS84."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def compute_name_similarity(name1: str, name2: str) -> float:
    """Calcule la similarité entre deux noms d'établissements (0.0 à 1.0)."""
    n1 = strip_accents(name1)
    n2 = strip_accents(name2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0

    tokens1 = set(re.findall(r"\w+", n1))
    tokens2 = set(re.findall(r"\w+", n2))
    if not tokens1 or not tokens2:
        return 0.0

    # Stop words médicaux génériques
    stop = {"dr", "docteur", "cabinet", "pharmacie", "clinique", "centre", "medical", "sante", "hopital", "el", "de", "la", "et", "du", "des"}
    c1 = tokens1 - stop
    c2 = tokens2 - stop
    if c1 and c2:
        overlap = len(c1 & c2) / max(len(c1), len(c2))
        if overlap >= 0.70:
            return overlap

    # Sequence matcher ratio
    return difflib.SequenceMatcher(None, n1, n2).ratio()


class NationalExpansionCollector(BaseCollector):
    """Collecteur multi-sources national avec déduplication et staging sécurisé."""

    def __init__(self, staging_db: str = STAGING_DB_PATH, prod_db: str = PROD_DB_PATH):
        super().__init__("national_expansion_osm", staging_db)
        self.prod_db = prod_db
        self.communes: List[Dict[str, Any]] = []
        self.commune_grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self.prod_grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self._load_communes()
        self._load_prod_grid()
        self._init_staging_db()

    def _load_communes(self):
        """Charge les 1 541 communes officielles et construit une grille spatiale (0.3° ~ 33 km)."""
        if not os.path.exists(COMMUNES_JSON_PATH):
            raise FileNotFoundError(f"Référentiel des communes introuvable : {COMMUNES_JSON_PATH}")

        with open(COMMUNES_JSON_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        for item in raw_data:
            geo = item.get("geo") or {}
            try:
                lat = float(geo.get("lat"))
                lon = float(geo.get("lon"))
                name_en = item.get("name", {}).get("en") or item.get("name", {}).get("slug")
                ancestors = item.get("ancestors", [{}])
                wilaya_name = ancestors[0].get("name", {}).get("en") or ""
                wilaya_code = ancestors[0].get("id", "").replace("DZ", "").lstrip("0")
                if len(wilaya_code) == 1:
                    wilaya_code = "0" + wilaya_code
                entry = {
                    "lat": lat,
                    "lon": lon,
                    "commune": name_en,
                    "wilaya": wilaya_name,
                    "wilaya_code": wilaya_code
                }
                self.communes.append(entry)

                cell = (int(lat / 0.3), int(lon / 0.3))
                self.commune_grid.setdefault(cell, []).append(entry)
            except (TypeError, ValueError):
                continue

    def _load_prod_grid(self):
        """Charge les 23 669 établissements de production en mode lecture seule dans une grille 0.01°."""
        if not os.path.exists(self.prod_db):
            raise FileNotFoundError(f"Base de production introuvable : {self.prod_db}")

        con = sqlite3.connect(f"file:{self.prod_db}?mode=ro", uri=True)
        cur = con.cursor()
        cur.execute("SELECT id, nom, latitude, longitude, telephone, wilaya, commune FROM places")
        rows = cur.fetchall()
        con.close()

        for pid, pnom, plat, plon, ptel, pwil, pcom in rows:
            if plat is None or plon is None:
                continue
            cell = (int(plat / 0.01), int(plon / 0.01))
            self.prod_grid.setdefault(cell, []).append({
                "id": pid,
                "nom": pnom,
                "nom_norm": strip_accents(pnom or ""),
                "lat": plat,
                "lon": plon,
                "tel": ptel,
                "wilaya": pwil,
                "commune": pcom
            })

    def _init_staging_db(self):
        """Initialise la table temporaire staging_new_places dans la base isolée sur D:."""
        os.makedirs(os.path.dirname(self.staging_db), exist_ok=True)
        con = sqlite3.connect(self.staging_db)
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS staging_new_places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id TEXT UNIQUE,
                nom TEXT NOT NULL,
                nom_normalized TEXT,
                categorie_recherche TEXT,
                type_google TEXT,
                wilaya TEXT NOT NULL,
                wilaya_code TEXT,
                commune TEXT NOT NULL,
                adresse TEXT,
                telephone TEXT,
                telephone_normalized TEXT,
                telephone_raw TEXT,
                site_web TEXT,
                horaires TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                google_maps_url TEXT,
                source TEXT DEFAULT 'osm_overpass_expansion_2026',
                status TEXT DEFAULT 'ACTIF',
                name_status TEXT DEFAULT 'CERTIFIED',
                name_source TEXT DEFAULT 'osm_overpass_expansion_2026',
                commune_source TEXT DEFAULT 'spatial_centroid_match',
                commune_confidence TEXT DEFAULT 'HIGH',
                geocoding_level TEXT DEFAULT 'EXACT_GPS',
                scrape_date TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS staging_duplicates_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_place_id TEXT,
                candidate_name TEXT,
                matched_prod_id INTEGER,
                matched_prod_name TEXT,
                distance_m REAL,
                name_similarity REAL,
                candidate_phone TEXT,
                prod_phone TEXT,
                phone_enriched INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_staging_place_id ON staging_new_places(place_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_staging_wilaya ON staging_new_places(wilaya)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_staging_coords ON staging_new_places(latitude, longitude)")

        con.commit()
        con.close()

    def find_nearest_commune(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Trouve la commune la plus proche via la grille spatiale indexée (rayon ~70 km)."""
        c_y, c_x = int(lat / 0.3), int(lon / 0.3)
        candidates = []
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                cell_items = self.commune_grid.get((c_y + dy, c_x + dx))
                if cell_items:
                    candidates.extend(cell_items)

        if not candidates:
            return None

        best_commune = None
        min_dist_m = float("inf")
        for c in candidates:
            dist = haversine_distance_m(lat, lon, c["lat"], c["lon"])
            if dist < min_dist_m:
                min_dist_m = dist
                best_commune = c
                if min_dist_m < 3000.0:  # < 3 km
                    break

        if best_commune and min_dist_m <= 55000.0:  # Dans un rayon de 55 km d'une commune algérienne
            res = dict(best_commune)
            res["distance_m"] = min_dist_m
            return res
        return None

    def map_category(self, tags: Dict[str, str], name: str) -> str:
        """Mappe les tags OSM vers l'une des 20 catégories standard de Medizy."""
        amenity = (tags.get("amenity") or "").lower().strip()
        healthcare = (tags.get("healthcare") or "").lower().strip()
        spec = (tags.get("healthcare:speciality") or "").lower().strip()
        name_lower = name.lower()

        if amenity == "pharmacy" or healthcare == "pharmacy" or "pharmacie" in name_lower or "صيدلية" in name_lower:
            return "pharmacie"
        if amenity == "hospital" or healthcare == "hospital" or "hopital" in name_lower or "hôpital" in name_lower or "مستشفى" in name_lower:
            return "hôpital"
        if amenity == "clinic" or healthcare == "clinic" or "clinique" in name_lower or "عيادة" in name_lower:
            return "clinique"
        if amenity == "dentist" or healthcare == "dentist" or "dentaire" in name_lower or "dentiste" in name_lower or "أسنان" in name_lower:
            return "cabinet dentaire"
        if healthcare in ("laboratory", "sample_collection") or "laboratoire" in name_lower or "مخبر" in name_lower:
            return "laboratoire médical"
        if healthcare == "centre" or "centre de santé" in name_lower or "polyclinique" in name_lower:
            return "centre de santé"
        if healthcare in ("physiotherapist", "physiotherapy") or "kiné" in name_lower or "kinesitherapeute" in name_lower:
            return "kinésithérapie"
        if healthcare == "optometrist" or "ophtalmo" in name_lower:
            return "ophtalmologue"
        if healthcare == "psychotherapist" or "psychol" in name_lower or "psychiat" in name_lower:
            return "psychologue"
        if healthcare in ("radiology", "imaging") or "radiologie" in name_lower or "imagerie" in name_lower:
            return "centre de radiologie"
        if amenity == "doctors" or healthcare == "doctor" or "docteur" in name_lower or "dr." in name_lower or "dr " in name_lower or "cabinet" in name_lower or "طبيب" in name_lower:
            return "cabinet médical"

        return "centre de santé"

    def normalize_phone_dz(self, raw_phone: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Nettoie le numéro de téléphone et le normalise au format algérien (0XXXXXXXXX)."""
        if not raw_phone:
            return None, None
        s = str(raw_phone).strip()
        raw_val = s

        # Rejet indicatifs étrangers (Espagne +34, Tunisie +216, Maroc +212, etc.)
        if re.search(r"^\+?(34|216|212|33|39|351)", s):
            return None, raw_val

        # Nettoyage indicatif international algérien
        s = re.sub(r"^\+213\s*\(0\)?", "0", s)
        s = re.sub(r"^\+213", "0", s)
        s = re.sub(r"^00213\s*\(0\)?", "0", s)
        s = re.sub(r"^00213", "0", s)

        digits = re.sub(r"[^\d]", "", s)
        if digits.startswith("213"):
            digits = "0" + digits[3:]
        elif not digits.startswith("0") and len(digits) == 9 and digits[0] in "234567":
            digits = "0" + digits

        # Numéro standard algérien valide : 9 ou 10 chiffres commençant par 0
        if len(digits) in (9, 10) and digits.startswith("0"):
            return digits, raw_val
        return None, raw_val

    def load_osm_raw_data(self) -> List[Dict[str, Any]]:
        """Charge les données brutes depuis le cache local ou déclenche la requête Overpass."""
        if os.path.exists(RAW_OSM_CACHE) and os.path.getsize(RAW_OSM_CACHE) > 1000000:
            print(f"[OK] Chargement du flux brut existant : {RAW_OSM_CACHE}")
            with open(RAW_OSM_CACHE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("elements", [])

        print(f"[OVERPASS] Téléchargement du flux national depuis {OVERPASS_URL}...")
        import urllib.request as request
        q = f"""[out:json][timeout:180][bbox:{BBOX_ALGERIA}];
        (
          node["amenity"~"hospital|clinic|pharmacy|doctors|dentist"];
          node["healthcare"];
          way["amenity"~"hospital|clinic|pharmacy"];
        );
        out center;
        """
        headers = {
            "User-Agent": "MedizyNationalExpansion/1.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        req = request.Request(OVERPASS_URL, data=q.encode("utf-8"), headers=headers)
        with request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        os.makedirs(os.path.dirname(RAW_OSM_CACHE), exist_ok=True)
        with open(RAW_OSM_CACHE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"[OK] Flux sauvegardé dans {RAW_OSM_CACHE}")
        return data.get("elements", [])

    def collect(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Exécute l'extraction, la déduplication et le staging complet."""
        elements = self.load_osm_raw_data()
        print(f"Total elements OSM bruts : {len(elements)}")

        staging_con = sqlite3.connect(self.staging_db)
        staging_cur = staging_con.cursor()

        # Vider la staging table pour garantir l'idempotence
        staging_cur.execute("DELETE FROM staging_new_places")
        staging_cur.execute("DELETE FROM staging_duplicates_log")
        staging_con.commit()

        # Grille mémoire des candidats retenus (pour déduplication interne nœuds/ways)
        accepted_grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}

        stats = {
            "total_raw": len(elements),
            "outside_algeria": 0,
            "without_name": 0,
            "existing_duplicates_prod": 0,
            "internal_duplicates_osm": 0,
            "phone_enrichments_identified": 0,
            "new_certified_places": 0,
            "by_wilaya": {},
            "by_category": {},
            "with_phone": 0,
            "with_website": 0,
            "with_gps": 0
        }

        now_iso = datetime.now().isoformat()
        t0 = time.time()

        for idx, el in enumerate(elements):
            if limit and stats["new_certified_places"] >= limit:
                break

            tags = el.get("tags") or {}

            # 1. Filtre pays étranger explicite
            if tags.get("addr:country") in ("ES", "TN", "MA", "PT", "GI", "IT", "FR"):
                stats["outside_algeria"] += 1
                continue

            # 2. Coordonnées GPS
            lat = el.get("lat")
            lon = el.get("lon")
            if lat is None or lon is None:
                center = el.get("center") or {}
                lat = center.get("lat")
                lon = center.get("lon")
            if lat is None or lon is None:
                continue

            # Bornes géographiques larges
            if not (18.5 <= lat <= 37.5 and -9.0 <= lon <= 12.5):
                stats["outside_algeria"] += 1
                continue

            # 3. Rattachement géographique à l'Algérie
            nearest_com = self.find_nearest_commune(lat, lon)
            if not nearest_com:
                stats["outside_algeria"] += 1
                continue

            # 4. Extraction du nom de l'établissement
            raw_name = tags.get("name") or tags.get("name:fr") or tags.get("name:ar") or tags.get("operator")
            if not raw_name or not raw_name.strip():
                stats["without_name"] += 1
                continue

            name = raw_name.strip()
            name_norm = strip_accents(name)

            # 5. Déduplication spatiale contre la base de production (< 60m & nom > 70%)
            c_y, c_x = int(lat / 0.01), int(lon / 0.01)
            is_prod_duplicate = False
            matched_prod_place = None
            max_sim = 0.0
            min_dist = float("inf")

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for p in self.prod_grid.get((c_y + dy, c_x + dx), []):
                        d_m = haversine_distance_m(lat, lon, p["lat"], p["lon"])
                        if d_m < 60.0:
                            sim = compute_name_similarity(name, p["nom"])
                            if sim >= 0.70:
                                is_prod_duplicate = True
                                matched_prod_place = p
                                max_sim = sim
                                min_dist = d_m
                                break
                    if is_prod_duplicate:
                        break
                if is_prod_duplicate:
                    break

            if is_prod_duplicate:
                stats["existing_duplicates_prod"] += 1
                cand_phone_norm, cand_phone_raw = self.normalize_phone_dz(tags.get("phone") or tags.get("contact:phone"))
                phone_enrich = 1 if (not matched_prod_place["tel"] and cand_phone_norm) else 0
                if phone_enrich:
                    stats["phone_enrichments_identified"] += 1

                staging_cur.execute("""
                    INSERT INTO staging_duplicates_log
                    (candidate_place_id, candidate_name, matched_prod_id, matched_prod_name, distance_m, name_similarity, candidate_phone, prod_phone, phone_enriched, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"osm:{el.get('type')}:{el.get('id')}",
                    name,
                    matched_prod_place["id"],
                    matched_prod_place["nom"],
                    round(min_dist, 2),
                    round(max_sim, 3),
                    cand_phone_norm,
                    matched_prod_place["tel"],
                    phone_enrich,
                    now_iso
                ))
                continue

            # 6. Déduplication interne contre les candidats déjà acceptés dans ce lot
            is_internal_dup = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for acc in accepted_grid.get((c_y + dy, c_x + dx), []):
                        d_m = haversine_distance_m(lat, lon, acc["lat"], acc["lon"])
                        if d_m < 50.0:
                            sim = compute_name_similarity(name, acc["nom"])
                            if sim >= 0.70:
                                is_internal_dup = True
                                break
                    if is_internal_dup:
                        break
                if is_internal_dup:
                    break

            if is_internal_dup:
                stats["internal_duplicates_osm"] += 1
                continue

            # 7. Normalisation finale de la fiche candidate
            category = self.map_category(tags, name)
            phone_norm, phone_raw = self.normalize_phone_dz(tags.get("phone") or tags.get("contact:phone") or tags.get("mobile"))
            website = tags.get("website") or tags.get("contact:website") or tags.get("url")
            horaires = tags.get("opening_hours")
            place_id = f"osm_overpass_expansion_2026:{el.get('type')}:{el.get('id')}"

            # Adresse
            addr_parts = []
            if tags.get("addr:street"):
                addr_parts.append(tags["addr:street"])
            if nearest_com["commune"]:
                addr_parts.append(nearest_com["commune"])
            if nearest_com["wilaya"]:
                addr_parts.append(nearest_com["wilaya"])
            adresse = ", ".join(addr_parts) if addr_parts else f"{nearest_com['commune']}, {nearest_com['wilaya']}"

            google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

            staging_cur.execute("""
                INSERT INTO staging_new_places (
                    place_id, nom, nom_normalized, categorie_recherche, type_google,
                    wilaya, wilaya_code, commune, adresse,
                    telephone, telephone_normalized, telephone_raw, site_web, horaires,
                    latitude, longitude, google_maps_url, source, status,
                    name_status, name_source, commune_source, commune_confidence,
                    geocoding_level, scrape_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                place_id, name, name_norm, category, category,
                nearest_com["wilaya"], nearest_com["wilaya_code"], nearest_com["commune"], adresse,
                phone_norm, phone_norm, phone_raw, website, horaires,
                round(lat, 7), round(lon, 7), google_maps_url, SOURCE_TAG, "ACTIF",
                "CERTIFIED", SOURCE_TAG, "spatial_centroid_match", "HIGH",
                "EXACT_GPS", now_iso[:10], now_iso, now_iso
            ))

            accepted_grid.setdefault((c_y, c_x), []).append({
                "nom": name,
                "lat": lat,
                "lon": lon
            })

            stats["new_certified_places"] += 1
            stats["with_gps"] += 1
            if phone_norm:
                stats["with_phone"] += 1
            if website:
                stats["with_website"] += 1

            wil_name = nearest_com["wilaya"]
            stats["by_wilaya"][wil_name] = stats["by_wilaya"].get(wil_name, 0) + 1
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

        staging_con.commit()
        staging_con.close()

        stats["execution_time_seconds"] = round(time.time() - t0, 2)
        print(f"\n[SUCCÈS] Expansion terminée en {stats['execution_time_seconds']}s :")
        print(f"  - Nouveaux établissements certifiés en staging : {stats['new_certified_places']}")
        print(f"  - Doublons éliminés vs production : {stats['existing_duplicates_prod']}")
        print(f"  - Doublons internes éliminés : {stats['internal_duplicates_osm']}")
        print(f"  - Éléments hors Algérie rejetés : {stats['outside_algeria']}")
        print(f"  - Éléments sans nom rejetés : {stats['without_name']}")

        with open(AUDIT_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        return stats


if __name__ == "__main__":
    collector = NationalExpansionCollector()
    res = collector.collect()
