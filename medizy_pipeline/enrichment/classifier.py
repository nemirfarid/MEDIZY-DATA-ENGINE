#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Classificateur et Normaliseur pour Établissements de Santé
=============================================================================
Identifie précisément la typologie des structures de santé publiques et privées
algériennes à partir du nom, des acronymes administratifs et des tags OSM/Google Places.
"""

import re
import unicodedata
from typing import Dict, Optional, Tuple

# Typologies officielles supportées dans le schéma MEDIZY
FACILITY_TYPES = [
    "CHU",
    "EPH",
    "EPSP",
    "EHS",
    "Hôpital",
    "Clinique",
    "Polyclinique",
    "Urgences",
    "Centre de Santé",
    "Dispensaire",
    "Cabinet Médical",
]


def strip_accents(text: Optional[str]) -> str:
    """Supprime les accents et normalise en bas de casse."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def normalize_text(text: Optional[str]) -> str:
    """Nettoie la chaîne : accents supprimés, ponctuation nettoyée, espaces consolidés."""
    if not text:
        return ""
    cleaned = strip_accents(text)
    # Remplacer la ponctuation courante par des espaces
    cleaned = re.sub(r"[\.,;:!\?_\-\(\)\[\]\{\}'\"/\\\|]", " ", cleaned)
    # Réduire les espaces multiples
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_algerian_phone(phone: Optional[str]) -> Tuple[str, str]:
    """
    Normalise un numéro de téléphone algérien.
    Retourne un tuple: (phone_e164, phone_display)
    Exemple: "021 23 45 67" -> ("+21321234567", "+213 21 23 45 67")
    """
    if not phone:
        return "", ""
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return "", ""

    # Gestion de l'indicatif international
    if digits.startswith("00213"):
        digits = digits[5:]
    elif digits.startswith("213"):
        digits = digits[3:]
    elif digits.startswith("0"):
        digits = digits[1:]

    # Les numéros en Algérie ont 9 chiffres après l'indicatif (fixe ou mobile)
    if len(digits) >= 9:
        digits = digits[:9]
        e164 = f"+213{digits}"
        # Format d'affichage avec le 0 local
        disp_digits = "0" + digits
        formatted = f"+213 {disp_digits[1:3]} {disp_digits[3:5]} {disp_digits[5:7]} {disp_digits[7:9]}"
        return e164, formatted

    return f"+213{digits}", f"+213{digits}"


def classify_facility(
    name: str,
    raw_tags: Optional[Dict[str, str]] = None,
    google_types: Optional[list] = None,
) -> str:
    """
    Détermine le type d'établissement selon la nomenclature de santé en Algérie.
    Ordre de priorité :
      1. Sigles hospitaliers publics stricts (CHU, EPH, EPSP, EHS, UMC)
      2. Mots clés structurels (Polyclinique, Clinique, Urgences, Dispensaire)
      3. Tags OSM (amenity=hospital, clinic, doctors) / Google Places types
    """
    raw_tags = raw_tags or {}
    google_types = google_types or []

    norm_name = " " + normalize_text(name) + " "

    # 1. Centre Hospitalo-Universitaire (CHU)
    if re.search(r"\b(chu|c\.h\.u|centre hospitalo universitaire|centre hospitalier universitaire)\b", norm_name):
        return "CHU"

    # 2. Établissement Public Hospitalier (EPH)
    if re.search(r"\b(eph|e\.p\.h|etablissement public hospitalier)\b", norm_name):
        return "EPH"

    # 3. Établissement Hospitalier Spécialisé (EHS)
    if re.search(r"\b(ehs|e\.h\.s|etablissement hospitalier specialise)\b", norm_name):
        return "EHS"

    # 4. Établissement Public de Santé de Proximité (EPSP)
    if re.search(r"\b(epsp|e\.p\.s\.p|etablissement public de sante de proximite)\b", norm_name):
        return "EPSP"

    # 5. Pavillon ou unité des Urgences
    if re.search(r"\b(urgences|urgence|umc|urgences medico chirurgicales|samu)\b", norm_name):
        return "Urgences"

    # 6. Polyclinique (publique ou sectorielle)
    if re.search(r"\b(polyclinique|poly clinique|polyclinik)\b", norm_name):
        return "Polyclinique"

    # 7. Clinique (souvent privée médico-chirurgicale ou spécialisée)
    if re.search(r"\b(clinique|clinic)\b", norm_name):
        return "Clinique"

    # 8. Centre de Santé / Dispensaire / Salle de soins
    if re.search(r"\b(dispensaire|salle de soins|salle de soin)\b", norm_name):
        return "Dispensaire"
    if re.search(r"\b(centre de sante|centre medical|centre medico social)\b", norm_name):
        return "Centre de Santé"

    # 9. Hôpital général ou militaire
    if re.search(r"\b(hopital|hospital|hmi|hopital militaire|hopital civil)\b", norm_name):
        return "Hôpital"

    # 10. Cabinet Médical / Médecin
    if re.search(r"\b(cabinet|docteur|dr|medecin)\b", norm_name):
        return "Cabinet Médical"

    # 11. Analyse via Tags OSM
    amenity = raw_tags.get("amenity", "").lower()
    healthcare = raw_tags.get("healthcare", "").lower()

    if amenity == "hospital" or healthcare == "hospital":
        return "Hôpital"
    if amenity == "clinic" or healthcare == "clinic":
        # Par défaut en Algérie, une "clinic" OSM sans autre mention est souvent une polyclinique ou clinique
        return "Clinique"
    if amenity == "doctors" or healthcare == "doctor":
        return "Cabinet Médical"

    # 12. Analyse via Google Places types
    if "hospital" in google_types:
        return "Hôpital"
    if "doctor" in google_types:
        return "Cabinet Médical"

    # Repli par défaut
    return "Clinique"
