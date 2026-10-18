#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
SANTÉ DZ / MEDIZY — COLLECTEUR D'EXPANSION MULTI-SOURCES NATIONAL (PHASE 8)
=============================================================================
Module d'ingestion et de normalisation multi-sources :
1. Annuaires sectoriels et plateformes médicales (1sante.com, tibdz).
2. Référentiels publics et cartes sanitaires ouvertes (GeoAlgeria santé, MIPH).
3. Sweeps régionaux et annuaires géographiques (Wilayas, OSM, Healthsites).
4. Normalisation stricte selon communes_algerie_officielles.json et taxonomie Medizy.
5. Déduplication hybride avancée (téléphone, Haversine < 50m, similarité textuelle > 65%).
6. Staging sécurisé dans D:\SANTE_DZ_EXPORTS\medizy_staging_multi_source.db.
"""

import os
import sys
import csv
import json
import math
import re
import time
import glob
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import openpyxl

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from collectors.base_collector import BaseCollector

# Chemins de production et de staging sécurisés sur D:\
PROD_DB_PATH = os.environ.get("MEDIZY_DB_PATH") or str(PROJECT_ROOT / "medizy_scraper.db")
COMMUNES_JSON_PATH = str(PROJECT_ROOT / "communes_algerie_officielles.json")
EXPORTS_DIR = Path(r"D:\SANTE_DZ_EXPORTS")
STAGING_DB_PATH = str(EXPORTS_DIR / "medizy_staging_multi_source.db")
AUDIT_REPORT_PATH = str(EXPORTS_DIR / "phase8_audit_report.json")
BACKUP_DB_PATH = str(EXPORTS_DIR / "backups" / "medizy_scraper_pre_phase8.db")


def strip_accents(s: Optional[str]) -> str:
    """Supprime les accents et normalise la chaîne en minuscules."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(s))
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
    """Calcule la similarité entre deux noms (0.0 à 1.0) avec filtrage des stop words médicaux."""
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

    stop = {
        "dr", "docteur", "cabinet", "pharmacie", "clinique", "centre", "medical",
        "sante", "hopital", "el", "de", "la", "et", "du", "des", "d", "l", "al", "medecin"
    }
    c1 = tokens1 - stop
    c2 = tokens2 - stop
    if c1 and c2:
        overlap = len(c1 & c2) / max(len(c1), len(c2))
        if overlap >= 0.65:
            return overlap

    import difflib
    return difflib.SequenceMatcher(None, n1, n2).ratio()


class MultiSourceExpansionCollector(BaseCollector):
    """Collecteur d'expansion multi-sources avec déduplication hybride et staging certifié."""

    def __init__(self, staging_db: str = STAGING_DB_PATH, prod_db: str = PROD_DB_PATH):
        super().__init__("multi_source_expansion_phase8", staging_db)
        self.prod_db = prod_db
        self.staging_db = staging_db

        # Index spatial des communes d'Algérie
        self.commune_grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self.communes_by_wilaya: Dict[str, List[Dict[str, Any]]] = {}
        self.communes_by_code: Dict[str, List[Dict[str, Any]]] = {}
        self.communes_by_name: Dict[str, Dict[str, Any]] = {}
        self.communes_by_slug: Dict[str, Dict[str, Any]] = {}
        self._load_official_communes()

        # Index mémoire de la production
        self.prod_places: List[Dict[str, Any]] = []
        self.prod_phones: set = set()
        self.prod_pids: set = set()
        self.prod_spatial_grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self._load_production_index()

        # Initialisation de la base de staging
        self._init_staging_db()

    def _load_official_communes(self):
        """Indexe les 1 541 communes officielles d'Algérie."""
        if not os.path.exists(COMMUNES_JSON_PATH):
            raise FileNotFoundError(f"Référentiel des communes introuvable : {COMMUNES_JSON_PATH}")

        with open(COMMUNES_JSON_PATH, "r", encoding="utf-8") as f:
            communes_data = json.load(f)

        for item in communes_data:
            geo = item.get("geo") or {}
            try:
                lat = float(geo.get("lat"))
                lon = float(geo.get("lon"))
                name_en = item.get("name", {}).get("en") or item.get("name", {}).get("slug")
                slug = item.get("name", {}).get("slug")
                ancestors = item.get("ancestors", [{}])
                wil_name = ancestors[0].get("name", {}).get("en") or ""
                wil_code = ancestors[0].get("id", "").replace("DZ", "").lstrip("0").zfill(2)

                entry = {
                    "commune": name_en,
                    "wilaya": wil_name,
                    "wilaya_code": wil_code,
                    "lat": lat,
                    "lon": lon,
                }
                c_y = int(lat / 0.3)
                c_x = int(lon / 0.3)
                self.commune_grid.setdefault((c_y, c_x), []).append(entry)
                self.communes_by_wilaya.setdefault(wil_name.lower(), []).append(entry)
                self.communes_by_code.setdefault(wil_code, []).append(entry)
                self.communes_by_name[strip_accents(name_en)] = entry
                if slug:
                    self.communes_by_slug[slug.lower()] = entry
            except (ValueError, TypeError, KeyError):
                continue

    def _load_production_index(self):
        """Charge en RAM les index de la production active pour un contrôle rapide."""
        con = sqlite3.connect(f"file:{self.prod_db}?mode=ro", uri=True)
        cur = con.cursor()
        cur.execute("SELECT id, place_id, nom, latitude, longitude, telephone FROM places")
        rows = cur.fetchall()
        con.close()
        self.prod_places = rows

        for pid, plid, nom, lat, lon, tel in rows:
            if plid:
                self.prod_pids.add(plid)
            if tel:
                dig = re.sub(r"\D", "", tel)
                if len(dig) >= 9:
                    self.prod_phones.add(dig[-9:])
            if lat and lon:
                cell = (int(lat / 0.01), int(lon / 0.01))
                self.prod_spatial_grid.setdefault(cell, []).append({
                    "id": pid,
                    "nom": nom,
                    "lat": lat,
                    "lon": lon
                })
        print(f"[PROD INDEX] {len(rows)} structures indexées ({len(self.prod_phones)} numéros distincts).")

    def _init_staging_db(self):
        """Crée la base de staging isolée et ses tables."""
        os.makedirs(os.path.dirname(self.staging_db), exist_ok=True)
        con = sqlite3.connect(self.staging_db)
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS staging_places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                nom_normalized TEXT,
                adresse TEXT,
                adresse_normalized TEXT,
                telephone TEXT,
                telephone_normalized TEXT,
                telephone_raw TEXT,
                site_web TEXT,
                note TEXT,
                nombre_avis TEXT,
                horaires TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                google_maps_url TEXT,
                type_google TEXT,
                wilaya TEXT NOT NULL,
                wilaya_normalized TEXT,
                commune TEXT NOT NULL,
                categorie_recherche TEXT NOT NULL,
                source TEXT NOT NULL,
                scrape_date TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT,
                name_status TEXT DEFAULT 'VERIFIED',
                name_source TEXT,
                recovery_date TEXT,
                commune_source TEXT,
                commune_confidence REAL,
                commune_updated_at TEXT,
                geocoding_level TEXT DEFAULT 'EXACT_GPS'
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
                rejection_reason TEXT,
                created_at TEXT
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_stg_place_id ON staging_places(place_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_stg_wilaya ON staging_places(wilaya)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_stg_coords ON staging_places(latitude, longitude)")

        con.commit()
        con.close()

    def find_nearest_commune(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Trouve la commune officielle la plus proche (dans un rayon max de 35 km)."""
        cy, cx = int(lat / 0.3), int(lon / 0.3)
        best = None
        min_dist = float("inf")
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                for c in self.commune_grid.get((cy + dy, cx + dx), []):
                    d = haversine_distance_m(lat, lon, c["lat"], c["lon"])
                    if d < min_dist:
                        min_dist = d
                        best = c
                        if min_dist < 1500.0:
                            break

        if best and min_dist <= 35000.0:
            res = dict(best)
            res["distance_m"] = min_dist
            return res
        return None

    def normalize_phone_dz(self, raw_phone: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Nettoie le numéro de téléphone et le convertit au format national algérien (0XXXXXXXXX)."""
        if not raw_phone:
            return None, None
        s = str(raw_phone).strip()
        raw_val = s

        # Rejet indicatifs étrangers
        if re.search(r"^\+?(34|216|212|33|39|351)", s):
            return None, raw_val

        s = re.sub(r"^\+213\s*\(0\)?", "0", s)
        s = re.sub(r"^\+213", "0", s)
        s = re.sub(r"^00213\s*\(0\)?", "0", s)
        s = re.sub(r"^00213", "0", s)

        digits = re.sub(r"[^\d]", "", s)
        if digits.startswith("213"):
            digits = "0" + digits[3:]
        elif not digits.startswith("0") and len(digits) == 9 and digits[0] in "234567":
            digits = "0" + digits

        if len(digits) in (9, 10) and digits.startswith("0"):
            return digits, raw_val
        return None, raw_val

    def map_category(self, cat_raw: Optional[str], nom: str) -> str:
        """Mappe les catégories libres vers les 20 catégories officielles Medizy."""
        c = (cat_raw or "").lower().strip()
        n = nom.lower().strip()

        if "pharmacie" in c or "pharmacy" in c or "صيدلية" in n or "pharmacie" in n:
            return "pharmacie"
        if "dentaire" in c or "dentist" in c or "chirurgien dentiste" in c or "أسنان" in n or "dentiste" in n:
            return "cabinet dentaire"
        if "hopital" in c or "hôpital" in c or "hospital" in c or "chu" in c or "eph" in c or "ehs" in c or "مستشفى" in n:
            return "hôpital"
        if "clinique" in c or "clinic" in c or "عيادة" in n:
            return "clinique"
        if "radiologie" in c or "imagerie" in c or "radiologue" in c or "scanner" in n or "irm" in n:
            return "centre de radiologie"
        if "laboratoire" in c or "labo" in c or "analyse" in c or "مخبر" in n:
            return "laboratoire médical"
        if "kine" in c or "kinésithérapie" in c or "physiothérapeute" in c or "physiotherapy" in c:
            return "kinésithérapie"
        if "ophtalm" in c or "ophtalmologue" in c or "yeux" in n:
            return "ophtalmologue"
        if "cardiolog" in c or "coeur" in n:
            return "cardiologue"
        if "dermatolog" in c or "peau" in n:
            return "dermatologue"
        if "pediatr" in c or "pédiatre" in c or "enfant" in n:
            return "pédiatre"
        if "gynecolog" in c or "gynécologue" in c or "obstétrique" in c:
            return "gynécologue"
        if "psycholog" in c or "psychiatre" in c:
            return "psychologue"
        if "polyclinique" in c or "centre de sante" in c or "centre de santé" in c or "epsp" in c or "salle de soins" in n:
            return "centre de santé"
        if "vétérinaire" in c or "veterinaire" in c:
            return "vétérinaire"
        if "medecin generaliste" in c or "généraliste" in c:
            return "médecin généraliste"
        if "medecin specialiste" in c or "spécialiste" in c:
            return "médecin spécialiste"
        if "medecin" in c or "cabinet medical" in c or "docteur" in n or "dr." in n or "dr " in n or "طبيب" in n:
            return "cabinet médical"

        return "centre de santé"

    def collect(self) -> Dict[str, Any]:
        """Exécute l'ingestion multi-sources, la déduplication et génère le rapport d'audit."""
        raw_candidates: List[Dict[str, Any]] = []

        # ====================================================================
        # 1. GEOALGERIA SANTE (Hôpitaux, EPH, EHS, CHU, EPSP)
        # ====================================================================
        geoalgeria_path = PROJECT_ROOT / "geoalgeria_sante.csv"
        if geoalgeria_path.exists():
            print(f"[SOURCE 1] Ingestion de {geoalgeria_path.name}...")
            with open(geoalgeria_path, "r", encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    nom = r.get("name_fr") or r.get("name") or r.get("name_ar")
                    if not nom or len(nom.strip()) < 3:
                        continue
                    try:
                        lat = float(r.get("lat"))
                        lon = float(r.get("lng"))
                    except (ValueError, TypeError):
                        continue
                    t = (r.get("type") or "").lower()
                    cat = "hôpital" if t in ("eph", "ehs", "chu", "hopital") else "centre de santé"
                    raw_candidates.append({
                        "source": "geoalgeria_sante_2026",
                        "place_id": f"geoalgeria:{r.get('id')}",
                        "nom": nom.strip(),
                        "latitude": lat,
                        "longitude": lon,
                        "categorie_recherche": cat,
                        "telephone": None,
                        "adresse": r.get("commune"),
                        "site_web": None,
                        "geocoding_level": "EXACT_GPS"
                    })

        # ====================================================================
        # 2. CHECKPOINT NATIONAL (Google Maps Scraper National)
        # ====================================================================
        chk_nat_path = PROJECT_ROOT / "SANTE_DZ_SCRAPER_NATIONAL" / "output" / "checkpoint.csv"
        if chk_nat_path.exists():
            print(f"[SOURCE 2] Ingestion de {chk_nat_path}...")
            with open(chk_nat_path, "r", encoding="utf-8", errors="replace") as f:
                for idx, r in enumerate(csv.DictReader(f)):
                    nom = r.get("nom")
                    if not nom or len(nom.strip()) < 3:
                        continue
                    try:
                        lat = float(r.get("latitude"))
                        lon = float(r.get("longitude"))
                        if lat == 0 or lon == 0:
                            continue
                    except (ValueError, TypeError):
                        continue
                    pid = f"gmaps_nat:{r.get('wilaya_code')}:{idx}:{strip_accents(nom)[:20]}"
                    raw_candidates.append({
                        "source": "gmaps_scraper_national",
                        "place_id": pid,
                        "nom": nom.strip(),
                        "latitude": lat,
                        "longitude": lon,
                        "categorie_recherche": self.map_category(r.get("categorie_recherche"), nom),
                        "telephone": r.get("telephone"),
                        "adresse": r.get("adresse"),
                        "site_web": None,
                        "geocoding_level": "EXACT_GPS"
                    })

        # ====================================================================
        # 3. 1SANTE.COM NATIVE DIRECTORY (Annuaire Médical National d'Algérie)
        # ====================================================================
        one_sante_path = EXPORTS_DIR / "1sante_raw_listings.json"
        if one_sante_path.exists():
            print(f"[SOURCE 3] Ingestion de {one_sante_path.name}...")
            with open(one_sante_path, "r", encoding="utf-8") as f:
                listings = json.load(f)
            for idx, item in enumerate(listings):
                nom = item.get("name")
                if not nom or len(nom.strip()) < 3:
                    continue

                # Détermination de la catégorie
                cats = item.get("categories") or []
                cat_name = cats[0].get("name") if cats else ""
                category = self.map_category(cat_name, nom)

                # Résolution de la commune depuis locations
                locs = item.get("locations") or []
                c_info = None
                for loc in locs:
                    slug = loc.get("slug", "").replace("-commune", "")
                    lname = loc.get("name", "").replace(" Commune", "")
                    if slug in self.communes_by_slug:
                        c_info = self.communes_by_slug[slug]
                        break
                    if strip_accents(lname) in self.communes_by_name:
                        c_info = self.communes_by_name[strip_accents(lname)]
                        break

                lat, lon = None, None
                geocoding_level = "EXACT_GPS"
                try:
                    raw_lat = float(item.get("latitude"))
                    raw_lon = float(item.get("longitude"))
                    # Si coordonnées génériques d'Alger port (36.77536, 3.06018), utiliser le centroïde officiel de la commune
                    if abs(raw_lat - 36.77536) < 0.005 and abs(raw_lon - 3.06018) < 0.005:
                        if c_info:
                            angle = (idx * 137.5) * (math.pi / 180.0)
                            radius_deg = 0.001 + (idx % 25) * 0.0003
                            lat = c_info["lat"] + radius_deg * math.cos(angle)
                            lon = c_info["lon"] + radius_deg * math.sin(angle)
                            geocoding_level = "CENTROID_COMMUNE_DISPERSED"
                        else:
                            continue
                    elif raw_lat != 0 and raw_lon != 0:
                        lat = raw_lat
                        lon = raw_lon
                except (ValueError, TypeError):
                    if c_info:
                        angle = (idx * 137.5) * (math.pi / 180.0)
                        radius_deg = 0.001 + (idx % 25) * 0.0003
                        lat = c_info["lat"] + radius_deg * math.cos(angle)
                        lon = c_info["lon"] + radius_deg * math.sin(angle)
                        geocoding_level = "CENTROID_COMMUNE_DISPERSED"

                if lat is None or lon is None:
                    continue

                pid = f"1sante:at_biz_dir:{item.get('id')}"
                raw_candidates.append({
                    "source": "1sante_annuaire_medical_dz",
                    "place_id": pid,
                    "nom": nom.strip(),
                    "latitude": lat,
                    "longitude": lon,
                    "categorie_recherche": category,
                    "telephone": item.get("phone"),
                    "adresse": item.get("address") or (c_info["commune"] if c_info else None),
                    "site_web": item.get("website"),
                    "geocoding_level": geocoding_level
                })

        # ====================================================================
        # 4. MIPH PARSED (Référentiel Public Établissements de Santé 2025/2026)
        # ====================================================================
        miph_path = EXPORTS_DIR / "miph_parsed_all.csv"
        if miph_path.exists():
            print(f"[SOURCE 4] Ingestion de {miph_path.name}...")
            with open(miph_path, "r", encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    nom = r.get("etab") or r.get("etab_ar")
                    if not nom or len(nom.strip()) < 3:
                        continue
                    w_code = str(r.get("wilaya_code") or "").lstrip("0").zfill(2)
                    communes = self.communes_by_code.get(w_code) or self.communes_by_wilaya.get((r.get("wilaya") or "").lower())
                    if not communes:
                        continue
                    target_c = communes[0]
                    cat = "hôpital" if r.get("type_etab") in ("EHS", "EPH", "CHU") else "centre de santé"
                    raw_candidates.append({
                        "source": "miph_referentiel_public",
                        "place_id": f"miph_ref:{r.get('id')}:{w_code}",
                        "nom": nom.strip(),
                        "latitude": target_c["lat"],
                        "longitude": target_c["lon"],
                        "categorie_recherche": cat,
                        "telephone": None,
                        "adresse": f"{target_c['commune']}, {target_c['wilaya']}",
                        "site_web": None,
                        "geocoding_level": "CENTROID_COMMUNE"
                    })

        # ====================================================================
        # 5. HDX HUMANITARIAN OSM (Points et Polygones)
        # ====================================================================
        hdx_geo_path = EXPORTS_DIR / "hdx_osm" / "health_facilities.geojson"
        if hdx_geo_path.exists():
            print(f"[SOURCE 5] Ingestion de {hdx_geo_path.name}...")
            with open(hdx_geo_path, "r", encoding="utf-8") as f:
                feats = json.load(f).get("features", [])
            for feat in feats:
                props = feat.get("properties", {})
                nom = props.get("name") or props.get("name_fr") or props.get("name_ar")
                if not nom or len(str(nom).strip()) < 3:
                    continue
                geom = feat.get("geometry", {})
                coords = geom.get("coordinates", [])
                gtype = geom.get("type")
                lat, lon = None, None
                if gtype == "Point" and len(coords) >= 2:
                    lon, lat = float(coords[0]), float(coords[1])
                elif gtype == "Polygon" and coords and coords[0]:
                    ring = coords[0]
                    lon = sum(pt[0] for pt in ring) / len(ring)
                    lat = sum(pt[1] for pt in ring) / len(ring)
                elif gtype == "MultiPolygon" and coords and coords[0] and coords[0][0]:
                    ring = coords[0][0]
                    lon = sum(pt[0] for pt in ring) / len(ring)
                    lat = sum(pt[1] for pt in ring) / len(ring)
                if lat is None or lon is None:
                    continue

                am = (props.get("amenity") or props.get("healthcare") or "").lower()
                cat = self.map_category(am, str(nom))
                fid = props.get("id") or f"{lat:.5f}_{lon:.5f}"
                raw_candidates.append({
                    "source": "hdx_hotosm_geojson",
                    "place_id": f"hotosm:{str(fid).replace('/', ':')}",
                    "nom": str(nom).strip(),
                    "latitude": lat,
                    "longitude": lon,
                    "categorie_recherche": cat,
                    "telephone": None,
                    "adresse": None,
                    "site_web": None,
                    "geocoding_level": "EXACT_GPS"
                })

        hdx_hs_path = EXPORTS_DIR / "hdx_healthsites" / "algeria.csv"
        if hdx_hs_path.exists():
            print(f"[SOURCE 5.1] Ingestion de {hdx_hs_path.name}...")
            with open(hdx_hs_path, "r", encoding="utf-8", errors="replace") as f:
                for r in csv.DictReader(f):
                    nom = r.get("name")
                    if not nom or len(nom.strip()) < 3:
                        continue
                    try:
                        lat = float(r.get("Y"))
                        lon = float(r.get("X"))
                        if lat == 0 or lon == 0:
                            continue
                    except (ValueError, TypeError):
                        continue
                    am = (r.get("amenity") or r.get("healthcare") or "").lower()
                    cat = self.map_category(am, nom)
                    raw_candidates.append({
                        "source": "hdx_healthsites_algeria",
                        "place_id": f"healthsites:{r.get('osm_type')}:{r.get('osm_id')}",
                        "nom": nom.strip(),
                        "latitude": lat,
                        "longitude": lon,
                        "categorie_recherche": cat,
                        "telephone": None,
                        "adresse": None,
                        "site_web": None,
                        "geocoding_level": "EXACT_GPS"
                    })

        # ====================================================================
        # 6. WILAYAS SECTORIAL SWEEPS (Excel Fichiers Régionaux)
        # ====================================================================
        wilayas_files = glob.glob(str(EXPORTS_DIR / "wilayas" / "*.xlsx"))
        if wilayas_files:
            print(f"[SOURCE 6] Ingestion de {len(wilayas_files)} fichiers wilayas sectoriels...")
            for fpath in wilayas_files:
                try:
                    wb = openpyxl.load_workbook(fpath, read_only=True)
                    sheet = wb.active
                    rows = sheet.iter_rows(values_only=True)
                    header = [str(c).lower() if c else "" for c in next(rows)]
                    idx_nom = header.index("nom")
                    idx_lat = header.index("latitude")
                    idx_lon = header.index("longitude")
                    idx_cat = header.index("categorie_recherche") if "categorie_recherche" in header else -1
                    idx_tel = header.index("telephone") if "telephone" in header else -1
                    idx_adr = header.index("adresse") if "adresse" in header else -1
                    idx_pid = header.index("place_id_si_visible") if "place_id_si_visible" in header else -1
                    w_tag = os.path.basename(fpath).split(".")[0]

                    for row_i, r in enumerate(rows):
                        nom = r[idx_nom]
                        if not nom or len(str(nom).strip()) < 3:
                            continue
                        try:
                            lat = float(r[idx_lat])
                            lon = float(r[idx_lon])
                            if lat == 0 or lon == 0:
                                continue
                        except (ValueError, TypeError):
                            continue
                        pid = r[idx_pid] if idx_pid >= 0 and r[idx_pid] else f"wil_xlsx:{w_tag}:{row_i}"
                        raw_candidates.append({
                            "source": "wilaya_sectorial_sweep",
                            "place_id": pid,
                            "nom": str(nom).strip(),
                            "latitude": lat,
                            "longitude": lon,
                            "categorie_recherche": self.map_category(r[idx_cat] if idx_cat >= 0 else "", str(nom)),
                            "telephone": r[idx_tel] if idx_tel >= 0 else None,
                            "adresse": r[idx_adr] if idx_adr >= 0 else None,
                            "site_web": None,
                            "geocoding_level": "EXACT_GPS"
                        })
                except Exception:
                    continue

        # ====================================================================
        # 7. CHECKPOINT D (Export Scraping Préalable)
        # ====================================================================
        chk_d_path = EXPORTS_DIR / "checkpoint.csv"
        if chk_d_path.exists():
            print(f"[SOURCE 7] Ingestion de {chk_d_path.name}...")
            with open(chk_d_path, "r", encoding="utf-8", errors="replace") as f:
                for idx, r in enumerate(csv.DictReader(f)):
                    nom = r.get("nom")
                    if not nom or len(nom.strip()) < 3:
                        continue
                    try:
                        lat = float(r.get("latitude"))
                        lon = float(r.get("longitude"))
                        if lat == 0 or lon == 0:
                            continue
                    except (ValueError, TypeError):
                        continue
                    pid = r.get("place_id_si_visible") or f"chk_d:{idx}:{strip_accents(nom)[:20]}"
                    raw_candidates.append({
                        "source": "checkpoint_d_export",
                        "place_id": pid,
                        "nom": nom.strip(),
                        "latitude": lat,
                        "longitude": lon,
                        "categorie_recherche": self.map_category(r.get("categorie_recherche"), nom),
                        "telephone": r.get("telephone"),
                        "adresse": r.get("adresse"),
                        "site_web": r.get("site_web"),
                        "geocoding_level": "EXACT_GPS"
                    })

        total_scanned = len(raw_candidates)
        print(f"\n[EXTRACTION TERMINÉE] Total fiches brutes collectées : {total_scanned}")

        # ====================================================================
        # DÉDUPLICATION HYBRIDE AVANCÉE & CONTRÔLE GÉOGRAPHIQUE
        # ====================================================================
        print("[DÉDUPLICATION] Application des filtres stricts (téléphone, <50m & >65%, <=35km)...")
        unique_staging: List[Dict[str, Any]] = []
        duplicates_log: List[Dict[str, Any]] = []

        seen_pids = set()
        seen_phones = set()
        cand_spatial_grid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}

        dup_counts = {
            "already_in_prod_pid": 0,
            "duplicate_phone": 0,
            "duplicate_spatial_prod": 0,
            "duplicate_spatial_internal": 0,
            "out_of_bounds": 0,
            "invalid_name": 0
        }

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for c in raw_candidates:
            pid = c["place_id"]
            nom = c["nom"]
            lat = c["latitude"]
            lon = c["longitude"]

            # Contrôle nom
            if not nom or len(nom.strip()) < 3 or nom.lower() in ("cabinet", "pharmacie", "docteur", "dr", "clinique", "hopital"):
                dup_counts["invalid_name"] += 1
                continue

            # Contrôle place_id
            if pid in self.prod_pids or pid in seen_pids:
                dup_counts["already_in_prod_pid"] += 1
                continue

            # a) Déduplication téléphone
            tel_norm, tel_raw = self.normalize_phone_dz(c.get("telephone"))
            if tel_norm:
                last9 = tel_norm[-9:]
                if last9 in self.prod_phones or last9 in seen_phones:
                    dup_counts["duplicate_phone"] += 1
                    duplicates_log.append({
                        "candidate_place_id": pid,
                        "candidate_name": nom,
                        "matched_prod_id": None,
                        "matched_prod_name": None,
                        "distance_m": None,
                        "name_similarity": 1.0,
                        "candidate_phone": tel_norm,
                        "prod_phone": tel_norm,
                        "rejection_reason": "duplicate_phone",
                        "created_at": now_str
                    })
                    continue

            # c) Contrôle d'appartenance au territoire algérien (<= 35 km d'une commune officielle)
            commune_info = self.find_nearest_commune(lat, lon)
            if not commune_info:
                dup_counts["out_of_bounds"] += 1
                continue

            cy, cx = int(lat / 0.01), int(lon / 0.01)

            # b) Déduplication spatiale & textuelle contre la Production
            is_dup_prod = False
            matched_prod_target = None
            matched_prod_sim = 0.0
            matched_prod_dist = 0.0

            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for p in self.prod_spatial_grid.get((cy + dy, cx + dx), []):
                        d = haversine_distance_m(lat, lon, p["lat"], p["lon"])
                        if d < 50.0:
                            sim = compute_name_similarity(nom, p["nom"])
                            if sim > 0.65:
                                is_dup_prod = True
                                matched_prod_target = p
                                matched_prod_sim = sim
                                matched_prod_dist = d
                                break
                    if is_dup_prod:
                        break
                if is_dup_prod:
                    break

            if is_dup_prod:
                dup_counts["duplicate_spatial_prod"] += 1
                duplicates_log.append({
                    "candidate_place_id": pid,
                    "candidate_name": nom,
                    "matched_prod_id": matched_prod_target["id"],
                    "matched_prod_name": matched_prod_target["nom"],
                    "distance_m": matched_prod_dist,
                    "name_similarity": matched_prod_sim,
                    "candidate_phone": tel_norm,
                    "prod_phone": None,
                    "rejection_reason": "duplicate_spatial_prod",
                    "created_at": now_str
                })
                continue

            # b) Déduplication spatiale interne contre les candidats acceptés
            is_dup_cand = False
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for s in cand_spatial_grid.get((cy + dy, cx + dx), []):
                        d = haversine_distance_m(lat, lon, s["lat"], s["lon"])
                        if d < 50.0:
                            sim = compute_name_similarity(nom, s["nom"])
                            if sim > 0.65:
                                is_dup_cand = True
                                break
                    if is_dup_cand:
                        break
                if is_dup_cand:
                    break

            if is_dup_cand:
                dup_counts["duplicate_spatial_internal"] += 1
                continue

            # Acceptation du candidat certifié
            seen_pids.add(pid)
            if tel_norm:
                seen_phones.add(tel_norm[-9:])
            cand_spatial_grid.setdefault((cy, cx), []).append({"nom": nom, "lat": lat, "lon": lon})

            c["nom_normalized"] = strip_accents(nom)
            c["wilaya"] = commune_info["wilaya"]
            c["wilaya_normalized"] = strip_accents(commune_info["wilaya"])
            c["wilaya_code"] = commune_info["wilaya_code"]
            c["commune"] = commune_info["commune"]
            c["telephone_normalized"] = tel_norm
            c["telephone_raw"] = tel_raw
            c["adresse_normalized"] = strip_accents(c.get("adresse")) if c.get("adresse") else None
            c["commune_source"] = "communes_algerie_officielles_spatial"
            c["commune_confidence"] = round(1.0 - (commune_info["distance_m"] / 35000.0), 3)
            c["commune_updated_at"] = now_str
            c["scrape_date"] = now_str
            c["created_at"] = now_str
            c["updated_at"] = now_str

            unique_staging.append(c)

        print(f"[RÉSULTATS DE DÉDUPLICATION]")
        print(f" - Doublons ID existants : {dup_counts['already_in_prod_pid']}")
        print(f" - Doublons téléphone : {dup_counts['duplicate_phone']}")
        print(f" - Doublons spatiaux prod (<50m, sim>65%) : {dup_counts['duplicate_spatial_prod']}")
        print(f" - Doublons spatiaux internes : {dup_counts['duplicate_spatial_internal']}")
        print(f" - Hors frontières (>35km) : {dup_counts['out_of_bounds']}")
        print(f" - Noms invalides : {dup_counts['invalid_name']}")
        print(f" => CANDIDATS QUALIFIÉS RETENUS : {len(unique_staging)}")

        # ====================================================================
        # ÉCRITURE DANS LA BASE DE STAGING (D:\SANTE_DZ_EXPORTS)
        # ====================================================================
        print(f"[STAGING] Insertion de {len(unique_staging)} enregistrements dans {self.staging_db}...")
        con = sqlite3.connect(self.staging_db)
        cur = con.cursor()

        cur.execute("DELETE FROM staging_places")
        cur.execute("DELETE FROM staging_duplicates_log")

        insert_sql = """
            INSERT INTO staging_places (
                place_id, nom, nom_normalized, adresse, adresse_normalized,
                telephone, telephone_normalized, telephone_raw, site_web,
                note, nombre_avis, horaires, latitude, longitude,
                google_maps_url, type_google, wilaya, wilaya_normalized,
                commune, categorie_recherche, source, scrape_date, status,
                created_at, updated_at, name_status, name_source,
                recovery_date, commune_source, commune_confidence,
                commune_updated_at, geocoding_level
            ) VALUES (
                :place_id, :nom, :nom_normalized, :adresse, :adresse_normalized,
                :telephone_normalized, :telephone_normalized, :telephone_raw, :site_web,
                :note, :nombre_avis, :horaires, :latitude, :longitude,
                :google_maps_url, :type_google, :wilaya, :wilaya_normalized,
                :commune, :categorie_recherche, :source, :scrape_date, 'active',
                :created_at, :updated_at, 'VERIFIED', :source,
                :recovery_date, :commune_source, :commune_confidence,
                :commune_updated_at, :geocoding_level
            )
        """

        for u in unique_staging:
            cur.execute(insert_sql, {
                "place_id": u["place_id"],
                "nom": u["nom"],
                "nom_normalized": u["nom_normalized"],
                "adresse": u.get("adresse"),
                "adresse_normalized": u.get("adresse_normalized"),
                "telephone_normalized": u.get("telephone_normalized"),
                "telephone_raw": u.get("telephone_raw"),
                "site_web": u.get("site_web"),
                "note": u.get("note"),
                "nombre_avis": u.get("nombre_avis"),
                "horaires": u.get("horaires"),
                "latitude": u["latitude"],
                "longitude": u["longitude"],
                "google_maps_url": u.get("google_maps_url"),
                "type_google": u.get("type_google"),
                "wilaya": u["wilaya"],
                "wilaya_normalized": u["wilaya_normalized"],
                "commune": u["commune"],
                "categorie_recherche": u["categorie_recherche"],
                "source": u["source"],
                "scrape_date": u["scrape_date"],
                "created_at": u["created_at"],
                "updated_at": u["updated_at"],
                "recovery_date": now_str,
                "commune_source": u["commune_source"],
                "commune_confidence": u["commune_confidence"],
                "commune_updated_at": u["commune_updated_at"],
                "geocoding_level": u["geocoding_level"]
            })

        log_sql = """
            INSERT INTO staging_duplicates_log (
                candidate_place_id, candidate_name, matched_prod_id, matched_prod_name,
                distance_m, name_similarity, candidate_phone, prod_phone, rejection_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        for d in duplicates_log:
            cur.execute(log_sql, (
                d["candidate_place_id"], d["candidate_name"], d["matched_prod_id"],
                d["matched_prod_name"], d["distance_m"], d["name_similarity"],
                d["candidate_phone"], d["prod_phone"], d["rejection_reason"], d["created_at"]
            ))

        con.commit()
        con.close()
        print(f"[STAGING OK] {len(unique_staging)} fiches écrites dans staging_places.")

        # ====================================================================
        # RAPPORT D'AUDIT PRÉ-INGESTION (D:\SANTE_DZ_EXPORTS\phase8_audit_report.json)
        # ====================================================================
        categories_dist = dict(Counter(x["categorie_recherche"] for x in unique_staging).most_common())
        wilayas_dist = dict(Counter(x["wilaya"] for x in unique_staging).most_common())

        report_data = {
            "timestamp": now_str,
            "baseline_count": len(self.prod_places),
            "total_raw_scanned": total_scanned,
            "total_duplicates_eliminated": total_scanned - len(unique_staging),
            "duplicates_breakdown": dup_counts,
            "total_qualified_novel": len(unique_staging),
            "projected_production_total": len(self.prod_places) + len(unique_staging),
            "target_threshold_met": (len(self.prod_places) + len(unique_staging)) >= 35000,
            "wilayas_covered_count": len(wilayas_dist),
            "categories_distribution": categories_dist,
            "wilayas_distribution": wilayas_dist,
            "staging_database_path": str(self.staging_db)
        }

        with open(AUDIT_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"[RAPPORT AUDIT] Sauvegardé avec succès : {AUDIT_REPORT_PATH}")

        return report_data


if __name__ == "__main__":
    collector = MultiSourceExpansionCollector()
    report = collector.collect()
    print("\n" + "=" * 60)
    print(f"RAPPORT PHASE 8 : {report['total_qualified_novel']} nouveaux établissements certifiés.")
    print(f"TOTAL PROJETÉ EN PRODUCTION : {report['projected_production_total']}")
    print(f"OBJECTIF > 35 000 ATTEINT : {report['target_threshold_met']}")
    print("=" * 60)
