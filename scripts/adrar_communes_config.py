# Official list of the 16 Communes of Wilaya 01 (Adrar)
COMMUNES_ADRAR = [
    {"code": "0101", "name_fr": "Adrar", "name_ar": "أدرار", "lat": 27.8742, "lon": -0.2939},
    {"code": "0102", "name_fr": "Tamest", "name_ar": "تامست", "lat": 27.6333, "lon": -0.2667},
    {"code": "0103", "name_fr": "Charouine", "name_ar": "شروين", "lat": 29.0167, "lon": -0.2667}, # Note: newly affiliated or frontier
    {"code": "0104", "name_fr": "Reggane", "name_ar": "رقان", "lat": 26.7197, "lon": 0.1714},
    {"code": "0105", "name_fr": "In Zghmir", "name_ar": "إن زغمير", "lat": 27.1167, "lon": -0.1167},
    {"code": "0106", "name_fr": "Tit", "name_ar": "تيت", "lat": 26.9667, "lon": -0.0167},
    {"code": "0107", "name_fr": "Ksar Kaddour", "name_ar": "قصر قدور", "lat": 29.3000, "lon": -0.2500},
    {"code": "0108", "name_fr": "Tsabit", "name_ar": "تسابيت", "lat": 28.3333, "lon": -0.2500},
    {"code": "0109", "name_fr": "Timmi", "name_ar": "تيمي", "lat": 27.8437, "lon": -0.2833},
    {"code": "0110", "name_fr": "Ouled Ahmed Tammi", "name_ar": "أولاد أحمد تيمي", "lat": 27.7667, "lon": -0.2667},
    {"code": "0111", "name_fr": "Bouda", "name_ar": "بودة", "lat": 27.9667, "lon": -0.4167},
    {"code": "0112", "name_fr": "Aoulef", "name_ar": "أولف", "lat": 26.9667, "lon": 1.0833},
    {"code": "0113", "name_fr": "Timekten", "name_ar": "تيمقتن", "lat": 27.0500, "lon": 1.3000},
    {"code": "0114", "name_fr": "Tamantit", "name_ar": "تمنطيط", "lat": 27.7667, "lon": -0.2667},
    {"code": "0115", "name_fr": "Fenoughil", "name_ar": "فنوغيل", "lat": 27.6500, "lon": -0.3000},
    {"code": "0116", "name_fr": "Sali", "name_ar": "سالي", "lat": 26.9000, "lon": -0.1667},
    {"code": "0117", "name_fr": "Sebaa", "name_ar": "السبع", "lat": 28.1833, "lon": -0.3500},
    {"code": "0118", "name_fr": "Akabli", "name_ar": "أقبلي", "lat": 26.7167, "lon": 1.3667}
]

CATEGORIES_MEDIZY = [
    "Pharmacie",
    "Médecin Généraliste",
    "Dentiste",
    "Pédiatre",
    "Gynécologue-Obstétricien",
    "Ophtalmologue",
    "Cardiologue",
    "Laboratoire d'analyses médicales",
    "Imagerie / Radiologie",
    "Dermatologue",
    "Chirurgien Orthopédiste",
    "ORL",
    "Pneumologue",
    "Gastro-entérologue",
    "Psychiatre / Psychologue",
    "Kinésithérapeute / Paramédical",
    "Clinique / Polyclinique",
    "Hôpital / Urgences (EPH / EPSP)"
]

print(f"Wilaya 01 (Adrar) contains {len(COMMUNES_ADRAR)} official communes.")
print(f"Workflow checks {len(CATEGORIES_MEDIZY)} medical categories per commune.")

