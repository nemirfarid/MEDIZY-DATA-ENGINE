# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Architecture Communes / Wilayas
====================================================
Objectif : préparer la couverture par commune pour maximiser le scraping
sans générer de doublons massifs.

Structure :
- WILAYAS : 58 wilayas officielles avec code et communes principales
- COMMUNES_BY_WILAYA : mapping wilaya -> liste de communes
- SEARCH_STRATEGY : stratégie de recherche par wilaya / commune

Règle d'or :
- Une recherche par wilaya couvre déjà la majorité des établissements.
- Les recherches par commune sont utilisées en complément pour :
  * les wilayas à forte densité (Alger, Oran, Constantine, Annaba...)
  * les communes spécifiques connues
  * les variantes de requêtes qui passent par une commune
"""

import json
from pathlib import Path
from typing import Dict, List

BASE = Path(__file__).resolve().parent

WILAYAS = [
    {"code": "01", "nom": "Adrar", "nom_ar": "أدرار"},
    {"code": "02", "nom": "Chlef", "nom_ar": "الشلف"},
    {"code": "03", "nom": "Laghouat", "nom_ar": "الأغواط"},
    {"code": "04", "nom": "Oum El Bouaghi", "nom_ar": "أم البواقي"},
    {"code": "05", "nom": "Batna", "nom_ar": "باتنة"},
    {"code": "06", "nom": "Béjaïa", "nom_ar": "بجاية"},
    {"code": "07", "nom": "Biskra", "nom_ar": "بسكرة"},
    {"code": "08", "nom": "Béchar", "nom_ar": "بشار"},
    {"code": "09", "nom": "Blida", "nom_ar": "البليدة"},
    {"code": "10", "nom": "Bouira", "nom_ar": "البويرة"},
    {"code": "11", "nom": "Tamanrasset", "nom_ar": "تمنراست"},
    {"code": "12", "nom": "Tébessa", "nom_ar": "تبسة"},
    {"code": "13", "nom": "Tlemcen", "nom_ar": "تلمسان"},
    {"code": "14", "nom": "Tiaret", "nom_ar": "تيارت"},
    {"code": "15", "nom": "Tizi Ouzou", "nom_ar": "تيزي وزو"},
    {"code": "16", "nom": "Alger", "nom_ar": "الجزائر"},
    {"code": "17", "nom": "Djelfa", "nom_ar": "الجلفة"},
    {"code": "18", "nom": "Jijel", "nom_ar": "جيجل"},
    {"code": "19", "nom": "Sétif", "nom_ar": "سطيف"},
    {"code": "20", "nom": "Saïda", "nom_ar": "سعيدة"},
    {"code": "21", "nom": "Skikda", "nom_ar": "سكيكدة"},
    {"code": "22", "nom": "Sidi Bel Abbès", "nom_ar": "سيدي بلعباس"},
    {"code": "23", "nom": "Annaba", "nom_ar": "عنابة"},
    {"code": "24", "nom": "Guelma", "nom_ar": "قالمة"},
    {"code": "25", "nom": "Constantine", "nom_ar": "قسنطينة"},
    {"code": "26", "nom": "Médéa", "nom_ar": "المدية"},
    {"code": "27", "nom": "Mostaganem", "nom_ar": "مستغانم"},
    {"code": "28", "nom": "M'Sila", "nom_ar": "المسيلة"},
    {"code": "29", "nom": "Mascara", "nom_ar": "معسكر"},
    {"code": "30", "nom": "Ouargla", "nom_ar": "ورقلة"},
    {"code": "31", "nom": "Oran", "nom_ar": "وهران"},
    {"code": "32", "nom": "El Bayadh", "nom_ar": "البيض"},
    {"code": "33", "nom": "Illizi", "nom_ar": "إليزي"},
    {"code": "34", "nom": "Bordj Bou Arréridj", "nom_ar": "برج بوعريريج"},
    {"code": "35", "nom": "Boumerdès", "nom_ar": "بومرداس"},
    {"code": "36", "nom": "El Tarf", "nom_ar": "الطارف"},
    {"code": "37", "nom": "Tindouf", "nom_ar": "تندوف"},
    {"code": "38", "nom": "Tissemsilt", "nom_ar": "تيسمسيلت"},
    {"code": "39", "nom": "El Oued", "nom_ar": "الوادي"},
    {"code": "40", "nom": "Khenchela", "nom_ar": "خنشلة"},
    {"code": "41", "nom": "Souk Ahras", "nom_ar": "سوق أهراس"},
    {"code": "42", "nom": "Tipaza", "nom_ar": "تيبازة"},
    {"code": "43", "nom": "Mila", "nom_ar": "ميلة"},
    {"code": "44", "nom": "Aïn Defla", "nom_ar": "عين الدفلى"},
    {"code": "45", "nom": "Naâma", "nom_ar": "النعامة"},
    {"code": "46", "nom": "Aïn Témouchent", "nom_ar": "عين تموشنت"},
    {"code": "47", "nom": "Ghardaïa", "nom_ar": "غرداية"},
    {"code": "48", "nom": "Relizane", "nom_ar": "غليزان"},
    {"code": "49", "nom": "Timimoun", "nom_ar": "تيميمون"},
    {"code": "50", "nom": "Bordj Badji Mokhtar", "nom_ar": "برج باجي مختار"},
    {"code": "51", "nom": "Ouled Djellal", "nom_ar": "أولاد جلال"},
    {"code": "52", "nom": "Béni Abbès", "nom_ar": "بني عباس"},
    {"code": "53", "nom": "In Salah", "nom_ar": "عين صالح"},
    {"code": "54", "nom": "In Guezzam", "nom_ar": "عين قزام"},
    {"code": "55", "nom": "Touggourt", "nom_ar": "تقرت"},
    {"code": "56", "nom": "Djanet", "nom_ar": "جانت"},
    {"code": "57", "nom": "El M'Ghair", "nom_ar": "المغير"},
    {"code": "58", "nom": "El Meniaa", "nom_ar": "المنيعة"},
]

# Communes principales par wilaya (liste non exhaustive, à enrichir)
# Format: wilaya_nom -> liste de communes
COMMUNES_BY_WILAYA: Dict[str, List[str]] = {
    "Adrar": ["Adrar", "Timimoun", "Reggane", "In Salah", "Tit"],
    "Chlef": ["Chlef", "El Karimia", "Ténès", "Ouled Farès", "Mozzag"],
    "Laghouat": ["Laghouat", "Aflou", "Boualem", "Sidi Makhlouf"],
    "Oum El Bouaghi": ["Oum El Bouaghi", "Aïn Beïda", "Aïn M'lila", "Meskiana"],
    "Batna": ["Batna", "Barika", "Aïn Djasser", "Tazoult", "Chemora"],
    "Béjaïa": ["Béjaïa", "Sidi Aïch", "Tichy", "El Kseur", "Ighil Ali"],
    "Biskra": ["Biskra", "Tolga", "El Kantara", "Ouled Djellal", "Sidi Khaled"],
    "Béchar": ["Béchar", "Kenadsa", "Lahmar", "Mechraa Houari Boumediene"],
    "Blida": ["Blida", "Boufarik", "Beni Mered", "Chiffa", "Ouled Yaïch"],
    "Bouira": ["Bouira", "El Adjiba", "Sour El Ghozlane", "Bechloul", "M'djebel"],
    "Tamanrasset": ["Tamanrasset", "Abalessa", "Tazrouk", "In Amguel"],
    "Tébessa": ["Tébessa", "Cheria", "El Kouif", "El Aouinet", "Morsott"],
    "Tlemcen": ["Tlemcen", "Maghnia", "Ghazaouet", "Nedroma", "Remchi"],
    "Tiaret": ["Tiaret", "Frenda", "Aïn Bouchekif", "Medroussa", "Dahmouni"],
    "Tizi Ouzou": ["Tizi Ouzou", "Azazga", "Azeffoun", "Larbaâ Nath Irathen", "Draâ Ben Khedda"],
    "Alger": ["Alger", "Bab El Oued", "El Mouradia", "Hydra", "Kouba", "Bir Mourad Raïs", "Bologhine", "Hussein Dey", "El Biar", "Draria", "Zeralda", "Cheraga", "Bouzaréah", "Djasr Kasentina", "Aïn Benian"],
    "Djelfa": ["Djelfa", "Messaad", "Aïn Oussera", "Hassi Bahbah", "Sidi Baizid"],
    "Jijel": ["Jijel", "El Milia", "Taher", "Chekfa", "Sidi Marouf"],
    "Sétif": ["Sétif", "El Eulma", "Bougaa", "Aïn Arnat", "Aïn Azel"],
    "Saïda": ["Saïda", "El Hassasna", "Maamora", "Ouled Khaled"],
    "Skikda": ["Skikda", "Annaba", "El Harrouch", "Azzaba", "Collo"],
    "Sidi Bel Abbès": ["Sidi Bel Abbès", "Télagh", "Mostefa Ben Brahim", "Sidi Brahim", "Ben Badis"],
    "Annaba": ["Annaba", "El Bouni", "Berrahal", "Eulma", "Aïn Berda"],
    "Guelma": ["Guelma", "Guelma B.Configuration", "Oued Zenati", "Héliopolis", "Bouchegouf"],
    "Constantine": ["Constantine", "El Khroub", "Aïn Smara", "Ibn Ziad", "Didouche Mourad"],
    "Médéa": ["Médéa", "Berrouaghia", "Aïn Boucif", "El Azizia", "Ouamri"],
    "Mostaganem": ["Mostaganem", "Aïn Tédelès", "Sidi Ali", "Mesra", "Achacha"],
    "M'Sila": ["M'Sila", "Bou Saâda", "El Hamel", "Tamsa", "Ouled Slimane"],
    "Mascara": ["Mascara", "Sig", "Mohammadia", "Tighennif", "Bouhanifia"],
    "Ouargla": ["Ouargla", "Rouissat", "Hassi Messaoud", "N'Goussa", "El Borma"],
    "Oran": ["Oran", "Arzew", "Bir El Djir", "Es Sénia", "Gdyel", "Misserghin", "Aïn El Turk", "Boutlelis", "Mers El Kébir"],
    "El Bayadh": ["El Bayadh", "Brezina", "El Abiodh Sidi Cheikh", "Bougtoub"],
    "Illizi": ["Illizi", "Djanet", "Debdeb", "Bordj Omar Driss"],
    "Bordj Bou Arréridj": ["Bordj Bou Arréridj", "Ras El Oued", "Mansoura", "El Achir", "Aïn Taghrout"],
    "Boumerdès": ["Boumerdès", "Boudouaou", "Boumerdès", "Tidjelabine", "Thenia", "Zemmouri"],
    "El Tarf": ["El Tarf", "Bouhadjar", "Besbes", "El Kala", "Ben M'hidi"],
    "Tindouf": ["Tindouf", "Oum El Assel"],
    "Tissemsilt": ["Tissemsilt", "Lazharia", "Beni Lahcene", "Ammal"],
    "El Oued": ["El Oued", "Debila", "Robbah", "Bayadha", "Taghzout"],
    "Khenchela": ["Khenchela", "El Hamma", "Aïn Touila", "El Oueldja", "Bouhmama"],
    "Souk Ahras": ["Souk Ahras", "M'Hdaur", "Bir Bouhouche", "Haddada", "Ouled Driss"],
    "Tipaza": ["Tipaza", "Cherchell", "Gouraya", "Hadjeret Ennous", "Sidi Amar"],
    "Mila": ["Mila", "Chelghoum Laïd", "Tadjenanet", "Oued Endja", "Bouhatem"],
    "Aïn Defla": ["Aïn Defla", "Médéa", "Khemis", "El Attaf", "Djendel"],
    "Naâma": ["Naâma", "Mecheria", "Ain Sefra", "Tiout", "Sfissifa"],
    "Aïn Témouchent": ["Aïn Témouchent", "El Amria", "Benzidjène", "Hassi El Ghella", "Ouled Kihal"],
    "Ghardaïa": ["Ghardaïa", "Metlili", "Dhayet Bendhahoua", "Berriane", "El Guerrara"],
    "Relizane": ["Relizane", "Mazouna", "Yellel", "Djidiouia", "Oued Rhiou"],
    "Timimoun": ["Timimoun", "Charouine", "Tinerkouk", "Deldoul"],
    "Bordj Badji Mokhtar": ["Bordj Badji Mokhtar"],
    "Ouled Djellal": ["Ouled Djellal", "Sidi Khaled", "Doucen", "El M'Ghair"],
    "Béni Abbès": ["Béni Abbès", "El Ouata", "Tabelbala", "Igli"],
    "In Salah": ["In Salah", "In Ghar", "Foggaret Ezzoua"],
    "In Guezzam": ["In Guezzam"],
    "Touggourt": ["Touggourt", "Nezla", "Megarine", "Taibet"],
    "Djanet": ["Djanet", "Bordj El Haouès"],
    "El M'Ghair": ["El M'Ghair", "Oum Touyour", "Still", "Sidi Khellil"],
    "El Meniaa": ["El Meniaa", "Hassi Gara", "Mansoura"],
}


# Stratégie de recherche
# - HIGH : wilayas à forte densité, recherche systématique par commune
# - MEDIUM : wilayates moyennes, recherche par commune seulement pour les chefs-lieux
# - LOW : wilayas désertiques, recherche uniquement par wilaya
DENSITY: Dict[str, str] = {
    "Alger": "HIGH",
    "Oran": "HIGH",
    "Constantine": "HIGH",
    "Annaba": "HIGH",
    "Sétif": "HIGH",
    "Tizi Ouzou": "HIGH",
    "Blida": "MEDIUM",
    "Béjaïa": "MEDIUM",
    "Tlemcen": "MEDIUM",
    "Batna": "MEDIUM",
    "Biskra": "MEDIUM",
    "Ouargla": "MEDIUM",
    "Skikda": "MEDIUM",
    "Médéa": "MEDIUM",
    "Mostaganem": "MEDIUM",
    "Mascara": "MEDIUM",
    "Boumerdès": "MEDIUM",
    "Jijel": "MEDIUM",
    "Mila": "MEDIUM",
    "Tipaza": "MEDIUM",
    "Relizane": "MEDIUM",
    "Saïda": "LOW",
    "Tissemsilt": "LOW",
    "Khenchela": "LOW",
    "Souk Ahras": "LOW",
    "El Oued": "LOW",
    "Naâma": "LOW",
    "Aïn Defla": "MEDIUM",
    "Aïn Témouchent": "MEDIUM",
    "Ghardaïa": "MEDIUM",
    "Tiaret": "MEDIUM",
    "El Bayadh": "LOW",
    "Bordj Bou Arréridj": "MEDIUM",
    "Bouira": "MEDIUM",
    "Djelfa": "MEDIUM",
    "Laghouat": "MEDIUM",
    "Oum El Bouaghi": "MEDIUM",
    "Tébessa": "MEDIUM",
    "Guelma": "MEDIUM",
    "M'Sila": "LOW",
    "Tamanrasset": "LOW",
    "Adrar": "LOW",
    "Béchar": "LOW",
    "Tindouf": "LOW",
    "Illizi": "LOW",
    "Timimoun": "LOW",
    "Bordj Badji Mokhtar": "LOW",
    "Ouled Djellal": "LOW",
    "Béni Abbès": "LOW",
    "In Salah": "LOW",
    "In Guezzam": "LOW",
    "Touggourt": "LOW",
    "Djanet": "LOW",
    "El M'Ghair": "LOW",
    "El Meniaa": "LOW",
    "El Tarf": "LOW",
    "Chlef": "MEDIUM",
    "Sidi Bel Abbès": "MEDIUM",
    "Jijel": "MEDIUM",
}

# default LOW for any missing
DEFAULT_DENSITY = "LOW"


def get_communes(wilaya_nom: str) -> List[str]:
    return COMMUNES_BY_WILAYA.get(wilaya_nom, [wilaya_nom])


def get_density(wilaya_nom: str) -> str:
    return DENSITY.get(wilaya_nom, DEFAULT_DENSITY)


def build_wilaya_commune_queries(wilaya_nom: str, categories: List[str]) -> List[Dict[str, str]]:
    """
    Retourne une liste de requêtes (wilaya, commune, query) à scraper.
    Pour HIGH/MEDIUM : wilaya + communes principales
    Pour LOW : uniquement wilaya
    """
    queries = []
    density = get_density(wilaya_nom)
    communes = get_communes(wilaya_nom) if density in ("HIGH", "MEDIUM") else []

    if density == "HIGH" and communes:
        # wilaya entière + chaque commune
        for cat in categories:
            queries.append({"wilaya": wilaya_nom, "commune": "", "query": f"{cat} {wilaya_nom} Algérie"})
        for commune in communes[:8]:  # limiter pour éviter explosion
            for cat in categories[:6]:  # catégories principales seulement
                queries.append({"wilaya": wilaya_nom, "commune": commune, "query": f"{cat} {commune} {wilaya_nom} Algérie"})
    elif density == "MEDIUM" and communes:
        # wilaya entière + chefs-lieux principaux
        for cat in categories:
            queries.append({"wilaya": wilaya_nom, "commune": "", "query": f"{cat} {wilaya_nom} Algérie"})
        for commune in communes[:4]:
            for cat in categories[:4]:
                queries.append({"wilaya": wilaya_nom, "commune": commune, "query": f"{cat} {commune} {wilaya_nom} Algérie"})
    else:
        # LOW : uniquement wilaya
        for cat in categories:
            queries.append({"wilaya": wilaya_nom, "commune": "", "query": f"{cat} {wilaya_nom} Algérie"})

    return queries
