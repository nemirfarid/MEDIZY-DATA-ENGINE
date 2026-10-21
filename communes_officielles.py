# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Référentiel officiel des communes d'Algérie
================================================================
Source : open-admin-data/algeria-administrative-divisions
Licence : CC-BY-4.0
Contenu : 58 wilayas, 548 dairas, 1541 communes avec noms bilingues,
codes postaux, coordonnées GPS.

Structure :
- WILAYAS : liste des wilayas
- COMMUNES_BY_WILAYA : mapping wilaya_code -> liste de communes
- COMMUNE_INDEX : index par nom (fr/ar) -> commune
- DETECTION : helper pour détecter la commune depuis une adresse
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

BASE = Path(__file__).resolve().parent
COMMUNES_FILE = BASE / "communes_algerie_officielles.json"

# Chargement paresseux
_wilayas = None
_communes_by_wilaya = None
_commune_index = None


def _load():
    global _wilayas, _communes_by_wilaya, _commune_index
    if _wilayas is not None:
        return
    if not COMMUNES_FILE.exists():
        raise FileNotFoundError(f"Référentiel communes introuvable : {COMMUNES_FILE}")
    data = json.loads(COMMUNES_FILE.read_text(encoding="utf-8"))
    # Filtrer uniquement les communes (level=3)
    communes = [r for r in data if r.get("level") == 3]
    _wilayas = {}
    _communes_by_wilaya = {}
    _commune_index = {}
    for c in communes:
        # Extraire le code wilaya depuis l'id (ex: DZ001_... -> 01)
        cid = c.get("id", "")
        wilaya_code = "00"
        if cid.startswith("DZ") and len(cid) >= 5:
            try:
                wilaya_code = str(int(cid[2:5])).zfill(2)
            except Exception:
                wilaya_code = "00"
        # Fallback : depuis ancestors
        if wilaya_code == "00":
            ancestors = c.get("ancestors", [])
            for anc in ancestors:
                if anc.get("level") == 1:
                    aid = anc.get("id", "")
                    if aid.startswith("DZ") and len(aid) >= 5:
                        try:
                            wilaya_code = str(int(aid[2:5])).zfill(2)
                        except Exception:
                            pass
                    break
        name_obj = c.get("name", {})
        name_fr = (name_obj.get("en") or name_obj.get("slug") or "").strip()
        name_ar = (name_obj.get("local") or "").strip()
        daira_obj = c.get("parent", {}) or {}
        daira = (daira_obj.get("name", {}) or {}).get("en", "").strip()
        zip_codes = [str(z).strip() for z in c.get("zip_codes", []) if str(z).strip()]
        geo = c.get("geo", {})
        lat = geo.get("lat")
        lng = geo.get("lon")
        entry = {
            "id": c.get("id", ""),
            "code": str(c.get("code", {}) or {}).strip(),
            "wilaya_code": wilaya_code,
            "nom_fr": name_fr,
            "nom_ar": name_ar,
            "daira": daira,
            "zip_codes": zip_codes,
            "latitude": float(lat) if lat else None,
            "longitude": float(lng) if lng else None,
        }
        _communes_by_wilaya.setdefault(wilaya_code, []).append(entry)
        if name_fr:
            _commune_index[name_fr.lower()] = entry
        if name_ar:
            _commune_index[name_ar] = entry
        for z in zip_codes:
            _commune_index[z] = entry
    # Trier les communes par nom
    for lst in _communes_by_wilaya.values():
        lst.sort(key=lambda x: x["nom_fr"].lower())


def get_wilayas() -> Dict[str, dict]:
    _load()
    return _wilayas


def get_communes_by_wilaya(wilaya_code: str) -> List[dict]:
    _load()
    return _communes_by_wilaya.get(str(wilaya_code).zfill(2), [])


def get_all_communes() -> List[dict]:
    _load()
    result = []
    for lst in _communes_by_wilaya.values():
        result.extend(lst)
    return result


def get_commune_by_name(name: str) -> Optional[dict]:
    _load()
    key = name.strip().lower()
    return _commune_index.get(key)


def get_commune_by_zip(zip_code: str) -> Optional[dict]:
    _load()
    return _commune_index.get(str(zip_code).strip())


def detect_commune_from_address(address: str) -> Optional[dict]:
    """Tente de détecter une commune officielle depuis une adresse brute."""
    if not address:
        return None
    _load()
    addr = address.lower()
    # Essayer par nom de commune
    for name, entry in _commune_index.items():
        if len(name) < 3:
            continue
        if name in addr:
            return entry
    # Essayer par code postal
    m = re.search(r"\b(\d{4,5})\b", address)
    if m:
        zip_entry = _commune_index.get(m.group(1))
        if zip_entry:
            return zip_entry
    return None


def build_wilaya_commune_queries(wilaya_code: str, categories: List[str], max_communes: int = 20) -> List[Dict[str, str]]:
    """
    Génère les requêtes de recherche pour une wilaya donnée.
    - wilaya_code : code wilaya sur 2 chiffres
    - categories : liste des catégories médicales
    - max_communes : limite le nombre de communes pour éviter explosion
    """
    _load()
    wilaya_code = str(wilaya_code).zfill(2)
    communes = get_communes_by_wilaya(wilaya_code)
    if not communes:
        return []
    # Trouver le nom de la wilaya depuis la première commune
    wilaya_nom = ""
    for c in communes:
        # remonter via ancestors si dispo
        break
    queries = []
    # Recherche générale par wilaya
    for cat in categories:
        queries.append({"wilaya_code": wilaya_code, "commune": "", "query": f"{cat} Algérie wilaya {wilaya_code}"})
    # Recherche par commune (limité)
    for commune in communes[:max_communes]:
        nom = commune.get("nom_fr", "")
        if not nom:
            continue
        for cat in categories[:6]:
            queries.append({
                "wilaya_code": wilaya_code,
                "commune": nom,
                "query": f"{cat} {nom} Algérie"
            })
    return queries
