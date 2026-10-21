# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Module de normalisation
============================================
Préserve systématiquement les valeurs RAW et produit des versions normalisées.

Règles :
- *_raw : valeur originale telle que collectée
- *_normalized : valeur normalisée (casse, espaces, accents, téléphones)
- Ne jamais écraser le champ RAW.
"""

import re
import unicodedata


def strip_accents(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_text(s: str) -> str:
    """lowercase, strip accents, collapse spaces."""
    if s is None:
        return ""
    s = str(s)
    s = strip_accents(s)
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_phone_raw(phone: str) -> str:
    """Normalise un numéro algérien vers +213XXXXXXXXX sans espace."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00213"):
        digits = digits[2:]  # 00213 -> 213
    elif digits.startswith("213"):
        digits = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        digits = digits[1:]
    if not digits.startswith("213"):
        digits = "213" + digits
    if len(digits) < 12:
        digits = digits + "0" * (12 - len(digits))
    return "+" + digits[:12]


def normalize_phone_display(phone: str) -> str:
    """Format d'affichage : +213 XX XX XX XX."""
    n = normalize_phone_raw(phone)
    if not n:
        return ""
    n = n.replace("+213", "").strip()
    if len(n) == 9:
        n = "0" + n
    parts = [n[i:i+2] for i in range(0, len(n), 2)]
    return "+213 " + " ".join(parts)


def normalize_wilaya(name: str) -> str:
    """Retourne le nom officiel si variante connue, sinon la valeur normalisée."""
    if not name:
        return ""
    n = normalize_text(name)
    # variantes courantes -> officiel
    mapping = {
        "tissemsilt": "Tissemsilt",
        "msila": "M'Sila",
        "el bayadh": "El Bayadh",
        "el oued": "El Oued",
        "ouargla": "Ouargla",
        "illizi": "Illizi",
        "tamanrasset": "Tamanrasset",
        "adrar": "Adrar",
        "chlef": "Chlef",
        "laghouat": "Laghouat",
        "oum el bouaghi": "Oum El Bouaghi",
        "batna": "Batna",
        "bejaia": "Béjaïa",
        "biskra": "Biskra",
        "bechar": "Béchar",
        "blida": "Blida",
        "bouira": "Bouira",
        "tebessa": "Tébessa",
        "tlemcen": "Tlemcen",
        "tiaret": "Tiaret",
        "tizi ouzou": "Tizi Ouzou",
        "alger": "Alger",
        "djelfa": "Djelfa",
        "jijel": "Jijel",
        "setif": "Sétif",
        "saida": "Saïda",
        "skikda": "Skikda",
        "sidi bel abbes": "Sidi Bel Abbès",
        "annaba": "Annaba",
        "guelma": "Guelma",
        "constantine": "Constantine",
        "medea": "Médéa",
        "mostaganem": "Mostaganem",
        "mascara": "Mascara",
        "oran": "Oran",
        "bordj bou arreridj": "Bordj Bou Arréridj",
        "boumerdes": "Boumerdès",
        "el tarf": "El Tarf",
        "tindouf": "Tindouf",
        "khenchela": "Khenchela",
        "souk ahras": "Souk Ahras",
        "tipaza": "Tipaza",
        "mila": "Mila",
        "ain defla": "Aïn Defla",
        "naama": "Naâma",
        "ain temouchent": "Aïn Témouchent",
        "ghardaia": "Ghardaïa",
        "relizane": "Relizane",
        "timimoun": "Timimoun",
        "bordj badji mokhtar": "Bordj Badji Mokhtar",
        "ouled djellal": "Ouled Djellal",
        "beni abbes": "Béni Abbès",
        "in salah": "In Salah",
        "in guezzam": "In Guezzam",
        "touggourt": "Touggourt",
        "djanet": "Djanet",
        "el mghair": "El M'Ghair",
        "el meniaa": "El Meniaa",
    }
    return mapping.get(n, name.strip())


def apply_normalization(row: dict) -> dict:
    """Ajoute les champs *_raw et *_normalized si absents, sans toucher aux originaux."""
    r = dict(row)
    # téléphone
    if "telephone_raw" not in r and r.get("telephone"):
        r["telephone_raw"] = r["telephone"]
    if "telephone_normalized" not in r:
        r["telephone_normalized"] = normalize_phone_raw(r.get("telephone", ""))
    # nom
    if "nom_raw" not in r and r.get("nom"):
        r["nom_raw"] = r["nom"]
    if "nom_normalized" not in r:
        r["nom_normalized"] = normalize_text(r.get("nom", ""))
    # adresse
    if "adresse_raw" not in r and r.get("adresse"):
        r["adresse_raw"] = r["adresse"]
    if "adresse_normalized" not in r:
        r["adresse_normalized"] = normalize_text(r.get("adresse", ""))
    # wilaya
    if "wilaya_normalized" not in r:
        r["wilaya_normalized"] = normalize_wilaya(r.get("wilaya", ""))
    return r
