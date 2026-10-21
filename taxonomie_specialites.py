# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Taxonomie des spécialités médicales
=========================================================
Deux objectifs :
1. Normaliser les intitulés de spécialités vers un vocabulaire contrôlé.
2. Servir de référence pour les variantes de recherche Google Maps.

Organisation :
- catégorie_generale (ex: Médecine)
- specialite (ex: Cardiologie)
- variantes_recherche (mots-clés pour le scraping)
- code_specialite (identifiant stable)
"""

from typing import Dict, List

# Vocabulaire contrôlé des spécialités / catégories santé
SPECIALITES: List[Dict[str, Any]] = [
    {
        "code": "MED-GEN",
        "categorie_generale": "Médecine",
        "specialite": "Médecine générale",
        "variantes_recherche": ["médecin généraliste", "médecin généraliste Algérie", "cabinet médecin généraliste"],
        "synonymes": ["généraliste", "médecin traitant", "médecin de famille"],
    },
    {
        "code": "CARDIO",
        "categorie_generale": "Médecine",
        "specialite": "Cardiologie",
        "variantes_recherche": ["cardiologue", "cardiologie", "cabinet cardiologie", "médecin cardiologue"],
        "synonymes": ["cardio", "spécialiste cœur"],
    },
    {
        "code": "DERMA",
        "categorie_generale": "Médecine",
        "specialite": "Dermatologie",
        "variantes_recherche": ["dermatologue", "dermatologie", "cabinet dermatologie", "médecin dermatologue"],
        "synonymes": ["dermato", "spécialiste peau"],
    },
    {
        "code": "PEDIA",
        "categorie_generale": "Médecine",
        "specialite": "Pédiatrie",
        "variantes_recherche": ["pédiatre", "pédiatrie", "cabinet pédiatrie", "médecin pédiatre"],
        "synonymes": ["pédiatre enfant", "spécialiste enfant"],
    },
    {
        "code": "GYNEC",
        "categorie_generale": "Médecine",
        "specialite": "Gynécologie",
        "variantes_recherche": ["gynécologue", "gynécologie", "cabinet gynécologie", "médecin gynécologue"],
        "synonymes": ["gynéco", "spécialiste femme"],
    },
    {
        "code": "OBST",
        "categorie_generale": "Médecine",
        "specialite": "Obstétrique",
        "variantes_recherche": ["obstétricien", "obstétrique", "gynécologue obstétricien"],
        "synonymes": ["sage-femme", "accouchement"],
    },
    {
        "code": "OPHTA",
        "categorie_generale": "Médecine",
        "specialite": "Ophtalmologie",
        "variantes_recherche": ["ophtalmologue", "ophtalmologie", "cabinet ophtalmologie", "médecin ophtalmologue"],
        "synonymes": ["ophtalmo", "spécialiste yeux", "ophtalmo"],
    },
    {
        "code": "ORL",
        "categorie_generale": "Médecine",
        "specialite": "Oto-rhino-laryngologie",
        "variantes_recherche": ["ORL", "oto-rhino-laryngologiste", "cabinet ORL"],
        "synonymes": ["ORL", "spécialiste oreille nez gorge"],
    },
    {
        "code": "URO",
        "categorie_generale": "Médecine",
        "specialite": "Urologie",
        "variantes_recherche": ["urologue", "urologie", "cabinet urologie", "médecin urologue"],
        "synonymes": ["urologue", "spécialiste urinaire"],
    },
    {
        "code": "NEURO",
        "categorie_generale": "Médecine",
        "specialite": "Neurologie",
        "variantes_recherche": ["neurologue", "neurologie", "cabinet neurologie", "médecin neurologue"],
        "synonymes": ["neuro", "spécialiste cerveau"],
    },
    {
        "code": "PSYCHIAT",
        "categorie_generale": "Médecine",
        "specialite": "Psychiatrie",
        "variantes_recherche": ["psychiatre", "psychiatrie", "cabinet psychiatrie", "médecin psychiatre"],
        "synonymes": ["psy", "spécialiste santé mentale"],
    },
    {
        "code": "PSYCHO",
        "categorie_generale": "Paramédical",
        "specialite": "Psychologie",
        "variantes_recherche": ["psychologue", "psychologie", "cabinet psychologie", "psychologue clinicien"],
        "synonymes": ["psycho", "thérapeute"],
    },
    {
        "code": "ENDO",
        "categorie_generale": "Médecine",
        "specialite": "Endocrinologie",
        "variantes_recherche": ["endocrinologue", "endocrinologie", "cabinet endocrinologie", "médecin endocrinologue"],
        "synonymes": ["endo", "spécialiste hormones"],
    },
    {
        "code": "GASTRO",
        "categorie_generale": "Médecine",
        "specialite": "Gastro-entérologie",
        "variantes_recherche": ["gastro-entérologue", "gastro-entérologie", "cabinet gastro", "médecin gastro-entérologue"],
        "synonymes": ["gastro", "spécialiste digestion"],
    },
    {
        "code": "PNEUMO",
        "categorie_generale": "Médecine",
        "specialite": "Pneumologie",
        "variantes_recherche": ["pneumologue", "pneumologie", "cabinet pneumologie", "médecin pneumologue"],
        "synonymes": ["pneumo", "spécialiste poumon"],
    },
    {
        "code": "NEPHRO",
        "categorie_generale": "Médecine",
        "specialite": "Néphrologie",
        "variantes_recherche": ["néphrologue", "néphrologie", "cabinet néphrologie", "médecin néphrologue"],
        "synonymes": ["néphro", "spécialiste rein"],
    },
    {
        "code": "ONCO",
        "categorie_generale": "Médecine",
        "specialite": "Oncologie",
        "variantes_recherche": ["oncologue", "oncologie", "cabinet oncologie", "médecin oncologue"],
        "synonymes": ["cancerologue", "spécialiste cancer"],
    },
    {
        "code": "ORTHO",
        "categorie_generale": "Médecine",
        "specialite": "Orthopédie",
        "variantes_recherche": ["orthopédiste", "orthopédie", "cabinet orthopédie", "médecin orthopédiste"],
        "synonymes": ["ortho", "spécialiste os"],
    },
    {
        "code": "RHEUMA",
        "categorie_generale": "Médecine",
        "specialite": "Rhumatologie",
        "variantes_recherche": ["rhumatologue", "rhumatologie", "cabinet rhumatologie", "médecin rhumatologue"],
        "synonymes": ["rhumato", "spécialiste articulation"],
    },
    {
        "code": "RADIO",
        "categorie_generale": "Médecine",
        "specialite": "Radiologie",
        "variantes_recherche": ["radiologue", "radiologie", "centre de radiologie", "radiologue Algérie"],
        "synonymes": ["radio", "imagerie médicale"],
    },
    {
        "code": "MED-INT",
        "categorie_generale": "Médecine",
        "specialite": "Médecine interne",
        "variantes_recherche": ["médecin interne", "médecine interne", "cabinet médecine interne"],
        "synonymes": ["interne"],
    },
    {
        "code": "CHIR",
        "categorie_generale": "Chirurgie",
        "specialite": "Chirurgie générale",
        "variantes_recherche": ["chirurgien", "chirurgie générale", "cabinet chirurgie"],
        "synonymes": ["chirurgien généraliste"],
    },
    {
        "code": "ANESTH",
        "categorie_generale": "Médecine",
        "specialite": "Anesthésie",
        "variantes_recherche": ["anesthésiste", "anesthésie", "cabinet anesthésie"],
        "synonymes": ["anesth"],
    },
    {
        "code": "KINE",
        "categorie_generale": "Paramédical",
        "specialite": "Kinésithérapie",
        "variantes_recherche": ["kinésithérapeute", "kinésithérapie", "cabinet kinésithérapie", "kiné"],
        "synonymes": ["kiné", "physiothérapie"],
    },
    {
        "code": "ORTHOPH",
        "categorie_generale": "Paramédical",
        "specialite": "Orthophonie",
        "variantes_recherche": ["orthophoniste", "orthophonie", "cabinet orthophonie"],
        "synonymes": ["orthophoniste"],
    },
    {
        "code": "SAGE-F",
        "categorie_generale": "Paramédical",
        "specialite": "Sage-femme",
        "variantes_recherche": ["sage-femme", "sage femme", "cabinet sage-femme"],
        "synonymes": ["sage-femme", "maïeuticienne"],
    },
    {
        "code": "NUTRI",
        "categorie_generale": "Paramédical",
        "specialite": "Nutrition",
        "variantes_recherche": ["nutritionniste", "nutrition", "cabinet nutrition", "diététicien"],
        "synonymes": ["nutrition", "diète"],
    },
    {
        "code": "OSTEO",
        "categorie_generale": "Paramédical",
        "specialite": "Ostéopathie",
        "variantes_recherche": ["ostéopathe", "ostéopathie", "cabinet ostéopathie"],
        "synonymes": ["ostéo"],
    },
    {
        "code": "DENT",
        "categorie_generale": "Dentaire",
        "specialite": "Dentisterie générale",
        "variantes_recherche": ["dentiste", "cabinet dentaire", "dentiste Algérie"],
        "synonymes": ["docteur dent", "chirurgien dentiste"],
    },
    {
        "code": "PHARMA",
        "categorie_generale": "Pharmacie",
        "specialite": "Pharmacie",
        "variantes_recherche": ["pharmacie", "pharmacien", "pharmacie de garde"],
        "synonymes": ["pharmacie", "drugstore"],
    },
    {
        "code": "CLINIQ",
        "categorie_generale": "Établissement",
        "specialite": "Clinique",
        "variantes_recherche": ["clinique", "clinique privée", "clinique Algérie"],
        "synonymes": ["clinique", "établissement de santé"],
    },
    {
        "code": "HOPITAL",
        "categorie_generale": "Établissement",
        "specialite": "Hôpital",
        "variantes_recherche": ["hôpital", "hôpital public", "EPSP", "centre hospitalier"],
        "synonymes": ["hôpital", "CHU", "EPS"],
    },
    {
        "code": "LABO",
        "categorie_generale": "Laboratoire",
        "specialite": "Laboratoire d'analyses médicales",
        "variantes_recherche": ["laboratoire médical", "laboratoire d'analyses", "laboratoire analyses médicales"],
        "synonymes": ["labo", "analyse médicale"],
    },
    {
        "code": "IMAG",
        "categorie_generale": "Imagerie",
        "specialite": "Imagerie médicale",
        "variantes_recherche": ["centre d'imagerie médicale", "centre de radiologie", "IRM", "scanner"],
        "synonymes": ["imagerie", "radio diagnostic"],
    },
    {
        "code": "VETO",
        "categorie_generale": "Vétérinaire",
        "specialite": "Médecine vétérinaire",
        "variantes_recherche": ["vétérinaire", "clinique vétérinaire", "cabinet vétérinaire"],
        "synonymes": ["vet", "vétérinaire"],
    },
]


def get_specialite_by_code(code: str) -> Dict[str, Any]:
    for s in SPECIALITES:
        if s["code"] == code:
            return s
    return {}


def normalize_specialite(text: str) -> str:
    """Retourne le code spécialité si match, sinon la valeur normalisée."""
    if not text:
        return ""
    t = text.lower().strip()
    for s in SPECIALITES:
        if t in [v.lower() for v in s.get("variantes_recherche", [])]:
            return s["code"]
        if t in [syn.lower() for syn in s.get("synonymes", [])]:
            return s["code"]
    return text.strip()


def build_search_variants(base_categories: List[str]) -> List[str]:
    """
    À partir des catégories de base, retourne des variantes de recherche enrichies
    sans générer d'explosion combinatorial inutile.
    """
    variants = set()
    for cat in base_categories:
        variants.add(cat)
        # variantes simples
        if "pharmacie" in cat.lower():
            variants.update(["pharmacie de garde", "pharmacie Algérie"])
        if "clinique" in cat.lower():
            variants.update(["clinique privée", "clinique Algérie"])
        if "hôpital" in cat.lower() or "centre de santé" in cat.lower():
            variants.update(["hôpital public", "EPSP", "centre hospitalier"])
        if "laboratoire" in cat.lower():
            variants.update(["laboratoire d'analyses médicales", "laboratoire analyses"])
        if "dentiste" in cat.lower() or "dentaire" in cat.lower():
            variants.update(["dentiste Algérie", "cabinet dentaire"])
        if "médecin" in cat.lower():
            variants.update(["médecin Algérie", "cabinet médical"])
    return sorted(variants)
