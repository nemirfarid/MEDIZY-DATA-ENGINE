#!/usr/bin/env python3
"""
Medizy - Correction des wilaya_code erronés pour les facilities

Problème : des facilities ont wilaya_code='58' mais leurs communes sont en wilaya 06 (Béjaïa, Aokas, Adekar).
Correction : mettre à jour wilaya_code vers la bonne wilaya basée sur la commune.
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "assets" / "data" / "sante_dz_bundled.db"


def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Charger la table communes : commune -> wilaya_code correct
    commune_to_wilaya = {}
    for row in cur.execute("SELECT wilaya_code, nom_fr FROM communes"):
        commune_to_wilaya[row["nom_fr"]] = row["wilaya_code"]

    # Identifier les facilities avec wilaya_code != wilaya de leur commune
    cur.execute("""
        SELECT id, nom, wilaya_code, commune
        FROM facilities
        WHERE commune IS NOT NULL AND commune != ''
    """)
    all_fac = cur.fetchall()

    mismatches = []
    for fac in all_fac:
        correct_wilaya = commune_to_wilaya.get(fac["commune"])
        if correct_wilaya and correct_wilaya != fac["wilaya_code"]:
            mismatches.append((fac["id"], fac["nom"], fac["wilaya_code"], fac["commune"], correct_wilaya))

    print(f"Facilities avec wilaya_code incorrect : {len(mismatches)}")
    for m in mismatches[:20]:
        print(f"  {m[1]}: wilaya {m[2]} -> {m[4]} (commune: {m[3]})")

    if mismatches:
        for fid, nom, old_wilaya, commune, new_wilaya in mismatches:
            # Mettre à jour wilaya_code, wilaya (nom), et coordonnées
            cur.execute("SELECT latitude, longitude FROM communes WHERE nom_fr = ? AND wilaya_code = ?", (commune, new_wilaya))
            row = cur.fetchone()
            if row and row["latitude"] is not None and row["longitude"] is not None:
                cur.execute(
                    "UPDATE facilities SET wilaya_code = ?, wilaya = ?, latitude = ?, longitude = ? WHERE id = ?",
                    (new_wilaya, get_wilaya_name(new_wilaya), row["latitude"], row["longitude"], fid),
                )
            else:
                # Juste le wilaya_code
                cur.execute(
                    "UPDATE facilities SET wilaya_code = ?, wilaya = ? WHERE id = ?",
                    (new_wilaya, get_wilaya_name(new_wilaya), fid),
                )

        conn.commit()
        print(f"\nCorrigé {len(mismatches)} facilities")

    # Vérification finale
    cur.execute("""
        SELECT COUNT(*) FROM facilities f
        JOIN communes c ON f.commune = c.nom_fr AND f.wilaya_code = c.wilaya_code
        WHERE f.commune IS NOT NULL AND f.commune != ''
    """)
    matched = cur.fetchone()[0]
    total = len(all_fac)
    print(f"Facilities avec wilaya correcte : {matched}/{total}")


def get_wilaya_name(code: str) -> str:
    names = {
        '01': 'Adrar', '02': 'Chlef', '03': 'Laghouat', '04': 'Oum El Bouaghi',
        '05': 'Batna', '06': 'Béjaïa', '07': 'Biskra', '08': 'Béchar',
        '09': 'Blida', '10': 'Bouira', '11': 'Tamanrasset', '12': 'Tébessa',
        '13': 'Tlemcen', '14': 'Tiaret', '15': 'Tizi Ouzou', '16': 'Alger',
        '17': 'Djelfa', '18': 'Jijel', '19': 'Sétif', '20': 'Saïda',
        '21': 'Skikda', '22': 'Sidi Bel Abbès', '23': 'Annaba', '24': 'Guelma',
        '25': 'Constantine', '26': 'Médéa', '27': 'Mostaganem', '28': 'M\'Sila',
        '29': 'Mascara', '30': 'Ouargla', '31': 'Oran', '32': 'El Bayadh',
        '33': 'Illizi', '34': 'Bordj Bou Arreridj', '35': 'Boumerdès', '36': 'El Tarf',
        '37': 'Tindouf', '38': 'Tissemsilt', '39': 'El Oued', '40': 'Khenchela',
        '41': 'Souk Ahras', '42': 'Tipaza', '43': 'Mila', '44': 'Aïn Defla',
        '45': 'Naâma', '46': 'Aïn Témouchent', '47': 'Ghardaïa', '48': 'Relizane',
        '49': 'Timimoun', '50': 'Bordj Badji Mokhtar', '51': 'Ouled Djellal',
        '52': 'Béni Abbès', '53': 'In Guezzam', '54': 'Touggourt',
        '55': 'El M\'Ghair', '56': 'El Meniaa', '57': 'Djanet', '58': 'In Salah',
    }
    return names.get(code, code)


if __name__ == "__main__":
    main()