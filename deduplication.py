# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Dédoublonage avec scoring pondéré
======================================================
Stratégie :

1. Calculer un score de similarité entre deux fiches.
2. Seuil :
   - >= 80 : fusion automatique
   - 60-79 : candidat à vérification manuelle (conservé séparé)
   - < 60 : établissements différents

Règles :
- place_id identique : +100
- téléphone normalisé identique + nom similaire : +50
- GPS très proches (< 50m) + nom similaire : +40
- nom très proche : +30
- adresse très proche : +30
- commune identique : +10

Les LOW (nom seul, adresse seule, nom+wilaya, adresse+wilaya) ne déclenchent
PAS de fusion automatique. Ils sont signalés comme candidats.
"""

import hashlib
import math
from typing import Dict, List, Optional, Tuple

from normalization import (
    apply_normalization,
    normalize_phone_raw,
    normalize_text,
)


# Seuils
AUTO_MERGE_THRESHOLD = 80
CANDIDATE_THRESHOLD = 60
GPS_MATCH_RADIUS_METERS = 50
NAME_SIMILARITY_MIN = 0.85


def _haversine_meters(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except Exception:
        return float("inf")
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _similarity_ratio(a: str, b: str) -> float:
    """Ratio de similarité entre deux chaînes normalisées."""
    a, b = normalize_text(a), normalize_text(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # Distance de Levenshtein normalisée
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0.0
    # matrice optimisée
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i]
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j-1] + cost))
        prev = curr
    dist = prev[n]
    max_len = max(m, n)
    return 1.0 - dist / max_len if max_len else 1.0


def _stable_key_legacy(row: dict) -> str:
    """Ancienne clé stable pour compatibilité."""
    raw = "|".join([
        normalize_text(row.get("nom", "")),
        normalize_text(row.get("adresse", "")),
        normalize_phone_raw(row.get("telephone", "")),
        str(row.get("latitude") or ""),
        str(row.get("longitude") or ""),
    ]).lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def compute_similarity_score(a: dict, b: dict) -> Tuple[int, str, List[str]]:
    """
    Calcule le score de similarité entre deux fiches.
    Retourne (score, niveau, raisons).
    Niveau : 'HIGH', 'MEDIUM', 'LOW', 'NONE'
    """
    raisons = []
    score = 0
    a = apply_normalization(a)
    b = apply_normalization(b)

    # 1. place_id identique (+100)
    pid_a = (a.get("place_id_si_visible") or "").strip()
    pid_b = (b.get("place_id_si_visible") or "").strip()
    if pid_a and pid_b and pid_a == pid_b:
        score += 100
        raisons.append("place_id identique")

    # 2. téléphone normalisé identique + nom similaire (+50)
    phone_a = (a.get("telephone_normalized") or "").strip()
    phone_b = (b.get("telephone_normalized") or "").strip()
    name_a = (a.get("nom_normalized") or "").strip()
    name_b = (b.get("nom_normalized") or "").strip()
    if phone_a and phone_b and phone_a == phone_b:
        if name_a and name_b and _similarity_ratio(name_a, name_b) >= NAME_SIMILARITY_MIN:
            score += 50
            raisons.append("téléphone identique + nom similaire")
        elif not name_a or not name_b:
            score += 40
            raisons.append("téléphone identique (nom manquant)")

    # 3. GPS très proches + nom similaire (+40)
    lat_a, lng_a = a.get("latitude"), a.get("longitude")
    lat_b, lng_b = b.get("latitude"), b.get("longitude")
    if lat_a and lng_a and lat_b and lng_b:
        dist = _haversine_meters(lat_a, lng_a, lat_b, lng_b)
        if dist <= GPS_MATCH_RADIUS_METERS:
            if name_a and name_b and _similarity_ratio(name_a, name_b) >= NAME_SIMILARITY_MIN:
                score += 40
                raisons.append(f"GPS proches ({dist:.1f}m) + nom similaire")
            elif not name_a or not name_b:
                score += 20
                raisons.append(f"GPS proches ({dist:.1f}m)")

    # 4. nom très proche (+30)
    if name_a and name_b:
        sim = _similarity_ratio(name_a, name_b)
        if sim >= NAME_SIMILARITY_MIN:
            score += 30
            raisons.append("nom très proche")

    # 5. adresse très proche (+30)
    addr_a = (a.get("adresse_normalized") or "").strip()
    addr_b = (b.get("adresse_normalized") or "").strip()
    if addr_a and addr_b:
        sim = _similarity_ratio(addr_a, addr_b)
        if sim >= NAME_SIMILARITY_MIN:
            score += 30
            raisons.append("adresse très proche")

    # 6. commune identique (+10)
    wilaya_a = (a.get("wilaya_normalized") or "").strip()
    wilaya_b = (b.get("wilaya_normalized") or "").strip()
    commune_a = (a.get("commune") or "").strip()
    commune_b = (b.get("commune") or "").strip()
    if commune_a and commune_b and commune_a.lower() == commune_b.lower():
        score += 10
        raisons.append("commune identique")
    elif wilaya_a and wilaya_b and wilaya_a == wilaya_b:
        # Bonus faible pour même wilaya (pas commune)
        score += 2
        raisons.append("wilaya identique")

    # Déterminer le niveau
    if score >= AUTO_MERGE_THRESHOLD:
        niveau = "HIGH"
    elif score >= CANDIDATE_THRESHOLD:
        niveau = "MEDIUM"
    elif score > 0:
        niveau = "LOW"
    else:
        niveau = "NONE"

    return score, niveau, raisons


def merge_rows(existing: dict, candidate: dict, score: int = 0, raisons: List[str] = None) -> dict:
    """
    Fusionne candidate dans existing en préservant toutes les données non vides.
    - existing n'est jamais écrasé par une valeur vide
    - les champs *_raw sont conservés si présents
    """
    merged = dict(existing)
    for key, value in candidate.items():
        if key.startswith("_"):
            continue
        if value is None:
            continue
        value_str = str(value).strip()
        if not value_str:
            continue
        if key in merged:
            existing_val = str(merged[key]).strip()
            if not existing_val:
                merged[key] = value_str
            elif len(value_str) > len(existing_val):
                merged[key] = value_str
        else:
            merged[key] = value_str
    # métadonnées de fusion
    merged["_merge_count"] = int(merged.get("_merge_count", 1)) + 1
    merged["_last_merged_at"] = candidate.get("scrape_date", merged.get("_last_merged_at", ""))
    if score:
        merged["_dedup_score"] = max(int(merged.get("_dedup_score", 0)), score)
    if raisons:
        existing_raisons = merged.get("_dedup_reasons", "")
        merged["_dedup_reasons"] = (existing_raisons + "; " + "; ".join(raisons)).strip("; ")
    return merged


class DeduplicationEngine:
    def __init__(self, auto_merge_threshold: int = AUTO_MERGE_THRESHOLD):
        self.auto_merge_threshold = auto_merge_threshold
        # Registry des fiches uniques par clé stable legacy
        self.unique: Dict[str, dict] = {}
        # Candidats de doublons (score < auto_merge_threshold)
        self.candidates: List[Tuple[dict, dict, int, str, List[str]]] = []

    def process(self, rows: List[dict]) -> Tuple[List[dict], Dict[str, int], List[dict]]:
        """
        Traite une liste de rows et retourne :
        (rows_dedupliquees, stats, candidats_à_vérifier)
        """
        stats = {
            "input": len(rows),
            "output": 0,
            "auto_merged": 0,
            "candidates": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
        }

        for row in rows:
            row = apply_normalization(row)
            row["_dedup_confidence"] = "NONE"
            row["_dedup_score"] = 0
            row["_dedup_reasons"] = ""

            # Vérifier les doublons avec les fiches existantes
            best_match = None
            best_score = 0
            best_reasons = []
            best_existing = None

            for existing in self.unique.values():
                score, niveau, raisons = compute_similarity_score(existing, row)
                if score > best_score:
                    best_score = score
                    best_reasons = raisons
                    best_existing = existing

            if best_score >= self.auto_merge_threshold:
                # Fusion automatique
                merged = merge_rows(best_existing, row, best_score, best_reasons)
                merged["_dedup_confidence"] = "HIGH"
                merged["_dedup_score"] = best_score
                merged["_dedup_reasons"] = "; ".join(best_reasons)
                # Remplacer l'ancienne entrée
                old_key = _stable_key_legacy(best_existing)
                self.unique.pop(old_key, None)
                new_key = _stable_key_legacy(merged)
                self.unique[new_key] = merged
                stats["auto_merged"] += 1
                stats["high_confidence"] += 1
            elif best_score >= CANDIDATE_THRESHOLD:
                # Candidat à vérification manuelle
                self.candidates.append((best_existing, row, best_score, "MEDIUM", best_reasons))
                stats["candidates"] += 1
                stats["medium_confidence"] += 1
                # Ajouter quand même la row comme nouvelle entrée pour ne pas perdre de données
                new_key = _stable_key_legacy(row)
                self.unique[new_key] = row
            else:
                # Nouvelle entrée
                new_key = _stable_key_legacy(row)
                self.unique[new_key] = row
                if best_score > 0:
                    stats["low_confidence"] += 1
                    row["_dedup_confidence"] = "LOW"
                    row["_dedup_score"] = best_score
                    row["_dedup_reasons"] = "; ".join(best_reasons)

        output = list(self.unique.values())
        stats["output"] = len(output)
        return output, stats, self.candidates
