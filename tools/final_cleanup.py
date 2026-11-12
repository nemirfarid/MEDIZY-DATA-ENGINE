#!/usr/bin/env python3
"""
Medizy - Nettoyage final des noms de communes restants

Après réparation automatique (Levenshtein) et manuelle, il reste 3 groupes de
facilities dont le `commune` ne matche pas la table `communes` :

1. "Bologhine" (16) -> déjà réparé en "Bologhine Ibnou Ziri" mais il reste des
   entrées avec le nom court. Corriger avec LIKE.
2. "Béjaïa" (58) -> 4 facilities en wilaya 58 dont les coordonnées pointent sur
   Adrar (wilaya 01). Ces facilities sont en fait en wilaya 01, commune Adrar.
3. "Draa Khellidja" (06) et "Bir Mchergua" (57) -> communes réelles absentes
   de la table `communes`. Les coordonnées sont déjà correctes (35.4,3.6 et
   33.5,5.8). Ajouter ces communes à la table `communes` pour permettre le mapping.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "assets" / "data" / "sante_dz_bundled.db"


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Corriger les Bologhine restants (LIKE)
    cur.execute(
        "UPDATE facilities SET commune = 'Bologhine Ibnou Ziri', latitude = 36.794, longitude = 3.04 "
        "WHERE commune LIKE 'Bologhine%' AND commune != 'Bologhine Ibnou Ziri'"
    )
    print(f"[1] Bologhine -> Bologhine Ibnou Ziri : {cur.rowcount} facilities")

    # 2. Corriger les 4 facilities Béjaïa en wilaya 58 -> wilaya 01, commune Adrar
    cur.execute(
        "UPDATE facilities SET commune = 'Adrar', wilaya_code = '01', wilaya = 'Adrar', "
        "latitude = 27.942, longitude = -0.215 "
        "WHERE commune LIKE 'Béjaïa%' AND wilaya_code = '58'"
    )
    print(f"[2] Béjaïa (58) -> Adrar (01) : {cur.rowcount} facilities")

    # 3. Ajouter les communes manquantes à la table `communes`
    # Draa Khellidja (06) - Kherrata, Béjaïa
    cur.execute(
        "INSERT OR IGNORE INTO communes (id, wilaya_code, nom_fr, nom_ar, daira, zip_code, latitude, longitude) "
        "VALUES ('DZ06_draa-khellidja_draa-khellidja', '06', 'Draa Khellidja', 'دراة خليجة', 'Kherrata', '06020', 35.4, 3.6)"
    )
    print(f"[3] Ajout commune Draa Khellidja (06)")

    # Bir Mchergua (57) - Ouled Gacem, El M'Ghair
    cur.execute(
        "INSERT OR IGNORE INTO communes (id, wilaya_code, nom_fr, nom_ar, daira, zip_code, latitude, longitude) "
        "VALUES ('DZ57_bir-mchergua_bir-mchergua', '57', 'Bir Mchergua', 'بئر مشرقة', 'El M''Ghair', '57010', 33.5, 5.8)"
    )
    print(f"[4] Ajout commune Bir Mchergua (57)")

    conn.commit()

    # Vérification finale
    fac = set(r["commune"] for r in cur.execute("SELECT DISTINCT commune FROM facilities WHERE commune IS NOT NULL AND commune != ''"))
    com = set(r["nom_fr"] for r in cur.execute("SELECT DISTINCT nom_fr FROM communes"))
    remaining = sorted(fac - com)
    print(f"\nRestant de communes non mappees : {len(remaining)}")
    for m in remaining:
        print(f"  - {m}")

    conn.close()


if __name__ == "__main__":
    main()