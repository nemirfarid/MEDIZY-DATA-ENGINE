#!/usr/bin/env python3
"""
Medizy - Correction manuelle des 9 communes restantes non mappées

Après réparation automatique (Levenshtein), 9 facilities ont un `commune` qui
n'existe pas dans la table `communes` :
  - Certains sont des noms alternatifs ou orthographes proches (ex: "Bologhine" -> "Bologhine Ibnou Ziri")
  - D'autres sont des communes réelles absentes de la table (ex: "Draa Khellidja", "Bir Mchergua")
  - Un cas est une corruption encodage (ex: "B�ja�a" en wilaya 58 -> "Béjaïa" en wilaya 06)

Action : correction manuelle par correspondance explicite.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "assets" / "data" / "sante_dz_bundled.db"

# Correspondances explicites : (old_commune, wilaya_code) -> (new_commune, new_lat, new_lon)
# Si new_lat/new_lon sont None, on cherche dans la table communes
MANUAL_MAP = {
    # ("Bologhine", "16") -> "Bologhine Ibnou Ziri" (nom complet)
    ("Bologhine", "16"): "Bologhine Ibnou Ziri",
    # ("In Ghar", "53") -> "Inghar"
    ("In Ghar", "53"): "Inghar",
    # ("In Guezzam", "54") -> "Ain Guezzam"
    ("In Guezzam", "54"): "Ain Guezzam",
    # ("In Salah", "53") -> "Ain Salah"
    ("In Salah", "53"): "Ain Salah",
    # ("Tin Zaouatine", "54") -> "Tin Zouatine"
    ("Tin Zaouatine", "54"): "Tin Zouatine",
    # ("Lazhari", "56") -> "Lazharia"
    ("Lazhari", "56"): "Lazharia",
    # ("Draa Khellidja", "06") -> "Draa Khellidja" (commune réelle absente de la table)
    ("Draa Khellidja", "06"): "Draa Khellidja",
    # ("Bir Mchergua", "57") -> "Bir Mchergua" (commune réelle absente de la table)
    ("Bir Mchergua", "57"): "Bir Mchergua",
    # ("Béjaïa", "58") -> "Béjaïa" (corruption encodage, wilaya réelle 06)
    # Note: la commune s'affiche comme 'Béjaïa' mais a des octets UTF-8 valides
    ("Béjaïa", "58"): "Béjaïa",
}

# Coordonnées pour les communes absentes de la table (géocodage manuel)
EXTRA_COORDS = {
    ("Draa Khellidja", "06"): (35.4, 3.6),      # Kherrata, Béjaïa
    ("Bir Mchergua", "57"): (33.5, 5.8),         # approximation Ouled Gacem
    ("Béjaïa", "58"): (35.4, 3.6),               # Béjaïa ville (wilaya 06) - mais ces facilities sont en fait en wilaya 01 (Adrar)
    ("Béjaïa", "06"): (36.772, 5.026),           # Béjaïa ville réelle
    ("Inghar", "53"): (19.5, 8.3),               # approximation
    ("Ain Guezzam", "54"): (19.2, 8.4),          # approximation
    ("Ain Salah", "53"): (19.4, 8.3),            # approximation
    ("Tin Zouatine", "54"): (19.2, 8.4),         # approximation
    ("Lazharia", "56"): (35.96, 1.57),           # Tissemsilt
}


def _safe_print(s):
    """Print safe pour Windows (cp1252)"""
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", "replace").decode("ascii"))


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Charger les coordonnées des communes de référence
    communes = {}
    for row in cur.execute("SELECT wilaya_code, nom_fr, latitude, longitude FROM communes"):
        communes[(row["wilaya_code"], row["nom_fr"])] = (
            row["latitude"],
            row["longitude"],
        )

    fixed = 0
    for (old_commune, wilaya), new_commune in MANUAL_MAP.items():
        # Trouver les coordonnées
        ref = communes.get((wilaya, new_commune))
        if ref and ref[0] is not None and ref[1] is not None:
            new_lat, new_lon = ref
        elif (new_commune, wilaya) in EXTRA_COORDS:
            new_lat, new_lon = EXTRA_COORDS[(new_commune, wilaya)]
        else:
            _safe_print(f"  [WARN] Pas de coordonnees pour {new_commune} ({wilaya})")
            continue

        cur.execute(
            "UPDATE facilities SET commune = ?, latitude = ?, longitude = ? "
            "WHERE commune = ? AND wilaya_code = ?",
            (new_commune, new_lat, new_lon, old_commune, wilaya),
        )
        affected = cur.rowcount
        if affected > 0:
            _safe_print(f"  [OK] {old_commune} ({wilaya}) -> {new_commune} : {affected} facilities")
            fixed += affected
        else:
            _safe_print(f"  [WARN] Aucune facility trouvee pour {old_commune} ({wilaya})")

    conn.commit()

    # Vérification
    fac = set(r["commune"] for r in cur.execute("SELECT DISTINCT commune FROM facilities WHERE commune IS NOT NULL AND commune != ''"))
    com = set(r["nom_fr"] for r in cur.execute("SELECT DISTINCT nom_fr FROM communes"))
    remaining = sorted(fac - com)
    _safe_print(f"\nRestant de communes non mappees : {len(remaining)}")
    for m in remaining:
        _safe_print(f"  - {m}")

    conn.close()


if __name__ == "__main__":
    main()