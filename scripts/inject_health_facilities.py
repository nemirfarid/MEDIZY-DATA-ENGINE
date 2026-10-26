#!/usr/bin/env python3
"""
Pipeline d'injection et de synchronisation massive de données de santé (MEDIZY).
Valide les coordonnées géographiques (Algérie), déduplique par proximité (< 10m)
et par numéro de téléphone, puis insère de manière atomique dans SQLite (facilities,
facilities_fts, facilities_rtree).
"""

import argparse
import csv
import json
import math
import os
import re
import sqlite3
import sys
from typing import Dict, List, Optional, Set, Tuple

# Référentiel officiel des 58 Wilayas d'Algérie
WILAYAS_58: Dict[str, str] = {
    '01': 'Adrar', '02': 'Chlef', '03': 'Laghouat', '04': 'Oum El Bouaghi',
    '05': 'Batna', '06': 'Béjaïa', '07': 'Biskra', '08': 'Béchar',
    '09': 'Blida', '10': 'Bouira', '11': 'Tamanrasset', '12': 'Tébessa',
    '13': 'Tlemcen', '14': 'Tiaret', '15': 'Tizi Ouzou', '16': 'Alger',
    '17': 'Djelfa', '18': 'Jijel', '19': 'Sétif', '20': 'Saïda',
    '21': 'Skikda', '22': 'Sidi Bel Abbès', '23': 'Annaba', '24': 'Guelma',
    '25': 'Constantine', '26': 'Médéa', '27': 'Mostaganem', '28': "M'Sila",
    '29': 'Mascara', '30': 'Ouargla', '31': 'Oran', '32': 'El Bayadh',
    '33': 'Illizi', '34': 'Bordj Bou Arréridj', '35': 'Boumerdès',
    '36': 'El Tarf', '37': 'Tindouf', '38': 'Tissemsilt', '39': 'El Oued',
    '40': 'Khenchela', '41': 'Souk Ahras', '42': 'Tipaza', '43': 'Mila',
    '44': 'Aïn Defla', '45': 'Naâma', '46': 'Aïn Témouchent', '47': 'Ghardaïa',
    '48': 'Relizane', '49': 'Timimoun', '50': 'Bordj Badji Mokhtar',
    '51': 'Ouled Djellal', '52': 'Béni Abbès', '53': 'In Salah',
    '54': 'In Guezzam', '55': 'Touggourt', '56': 'Djanet',
    '57': "El M'Ghair", '58': 'El Meniaa'
}

def normalize_text(text: str) -> str:
    """Normalise les accents et minuscules pour la comparaison."""
    if not text:
        return ""
    t = text.lower().strip()
    replacements = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'ö': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', '-': ' ', "'": ' ', "’": ' '
    }
    for k, v in replacements.items():
        t = t.replace(k, v)
    return re.sub(r'\s+', ' ', t).strip()

# Table inverse de résolution du code wilaya par nom normalisé
WILAYA_NAME_TO_CODE = {normalize_text(name): code for code, name in WILAYAS_58.items()}
# Variantes courantes
WILAYA_NAME_TO_CODE['algiers'] = '16'
WILAYA_NAME_TO_CODE['bejaia'] = '06'
WILAYA_NAME_TO_CODE['tebessa'] = '12'
WILAYA_NAME_TO_CODE['setif'] = '19'
WILAYA_NAME_TO_CODE['saida'] = '20'
WILAYA_NAME_TO_CODE['medea'] = '26'
WILAYA_NAME_TO_CODE['boumerdes'] = '35'
WILAYA_NAME_TO_CODE['ain defla'] = '44'
WILAYA_NAME_TO_CODE['ain temouchent'] = '46'
WILAYA_NAME_TO_CODE['ghardaia'] = '47'
WILAYA_NAME_TO_CODE['beni abbes'] = '52'
WILAYA_NAME_TO_CODE['el menghair'] = '57'
WILAYA_NAME_TO_CODE['el menia'] = '58'

def resolve_wilaya(wilaya_input: str, wilaya_code_input: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Résout le code et le nom officiel d'une Wilaya."""
    if wilaya_code_input:
        code = str(wilaya_code_input).strip().zfill(2)
        if code in WILAYAS_58:
            return code, WILAYAS_58[code]

    if not wilaya_input:
        return None, None

    raw = str(wilaya_input).strip()
    if raw.isdigit():
        code = raw.zfill(2)
        if code in WILAYAS_58:
            return code, WILAYAS_58[code]

    norm = normalize_text(raw)
    if norm in WILAYA_NAME_TO_CODE:
        code = WILAYA_NAME_TO_CODE[norm]
        return code, WILAYAS_58[code]

    return None, raw

def normalize_phone(phone: Optional[str]) -> str:
    """Normalise un numéro de téléphone algérien."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if not digits:
        return ""
    # Gestion de l'indicatif international +213 ou 00213
    if digits.startswith('213'):
        digits = '0' + digits[3:]
    elif digits.startswith('00213'):
        digits = '0' + digits[5:]
    if len(digits) == 9 and digits.startswith(('5', '6', '7', '2', '3', '4')):
        digits = '0' + digits
    return digits

def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Vérifie que les coordonnées GPS se situent strictement dans le territoire algérien :
    Latitude : 18.0°N à 38.0°N
    Longitude : -9.0°E à 12.0°E
    """
    return (18.0 <= lat <= 38.0) and (-9.0 <= lon <= 12.0)

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcule la distance géodésique de Haversine en mètres."""
    r = 6371000.0  # Rayon de la Terre en mètres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c

class HealthFacilityInjector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Base de données introuvable : {db_path}")
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()

    def load_existing_phones(self) -> Set[str]:
        """Charge l'index des numéros de téléphone existants pour déduplication rapide."""
        self.cur.execute("SELECT telephone FROM facilities WHERE telephone IS NOT NULL AND telephone != ''")
        phones = set()
        for (p,) in self.cur.fetchall():
            norm = normalize_phone(p)
            if len(norm) >= 8:
                phones.add(norm)
        return phones

    def is_proximity_duplicate(self, lat: float, lon: float, threshold_meters: float = 10.0) -> bool:
        """
        Vérifie via l'index spatial R-Tree si un établissement existe déjà à moins de 10 mètres.
        """
        margin = 0.00025  # ~ 27m de bounding-box
        min_lat = lat - margin
        max_lat = lat + margin
        min_lon = lon - margin
        max_lon = lon + margin

        query = """
            SELECT f.id, f.latitude, f.longitude
            FROM facilities_rtree r
            JOIN facilities f ON f.id = r.id
            WHERE r.min_lat <= ? AND r.max_lat >= ?
              AND r.min_lon <= ? AND r.max_lon >= ?
        """
        self.cur.execute(query, (max_lat, min_lat, max_lon, min_lon))
        candidates = self.cur.fetchall()
        for cid, clat, clon in candidates:
            dist = haversine_distance_meters(lat, lon, clat, clon)
            if dist < threshold_meters:
                return True
        return False

    def get_next_id(self) -> int:
        """Détermine le prochain ID primaire auto-incrémenté."""
        self.cur.execute("SELECT coalesce(max(id), 0) + 1 FROM facilities")
        return self.cur.fetchone()[0]

    def inject_dataset(self, facilities_data: List[Dict], dry_run: bool = False) -> Dict[str, int]:
        """
        Valide, filtre et insère atomiquement les établissements de santé.
        """
        stats = {
            'total_received': len(facilities_data),
            'inserted': 0,
            'rejected_invalid_gps': 0,
            'rejected_duplicate_phone': 0,
            'rejected_duplicate_proximity': 0,
            'rejected_missing_name': 0,
        }

        existing_phones = self.load_existing_phones()
        new_batch_points: List[Tuple[float, float]] = []
        new_batch_phones: Set[str] = set()

        next_id = self.get_next_id()
        rows_to_insert = []

        print(f"\n[>] Démarrage de l'analyse du lot ({len(facilities_data)} fiches)...")

        for idx, item in enumerate(facilities_data, start=1):
            nom = str(item.get('nom', '')).strip()
            if not nom:
                stats['rejected_missing_name'] += 1
                continue

            # 1. Validation des coordonnées GPS
            try:
                lat = float(item['latitude'])
                lon = float(item['longitude'])
            except (ValueError, KeyError, TypeError):
                stats['rejected_invalid_gps'] += 1
                continue

            if not validate_coordinates(lat, lon):
                stats['rejected_invalid_gps'] += 1
                continue

            # 2. Déduplication par numéro de téléphone
            raw_phone = item.get('telephone') or ''
            norm_phone = normalize_phone(raw_phone)
            if norm_phone and len(norm_phone) >= 8:
                if norm_phone in existing_phones or norm_phone in new_batch_phones:
                    stats['rejected_duplicate_phone'] += 1
                    continue

            # 3. Déduplication par proximité géographique (< 10 mètres)
            if self.is_proximity_duplicate(lat, lon, threshold_meters=10.0):
                stats['rejected_duplicate_proximity'] += 1
                continue

            is_batch_duplicate = False
            for (blat, blon) in new_batch_points:
                if haversine_distance_meters(lat, lon, blat, blon) < 10.0:
                    is_batch_duplicate = True
                    break
            if is_batch_duplicate:
                stats['rejected_duplicate_proximity'] += 1
                continue

            # 4. Résolution de la Wilaya et Commune
            wilaya_in = item.get('wilaya') or ''
            wilaya_code_in = item.get('wilaya_code')
            w_code, w_name = resolve_wilaya(wilaya_in, wilaya_code_in)
            if not w_code:
                w_code = '16'
                w_name = 'Alger'

            commune = str(item.get('commune') or w_name).strip()
            categorie = str(item.get('categorie') or item.get('specialite') or 'cabinet médical').strip().lower()
            adresse = str(item.get('adresse') or '').strip()
            site_web = str(item.get('site_web') or '').strip()
            place_id = str(item.get('place_id') or f"medizy_inj_{next_id}")
            source = str(item.get('source') or 'Import MEDIZY National')
            note = float(item.get('note', 4.5)) if item.get('note') is not None else 4.5
            nombre_avis = int(item.get('nombre_avis', 1)) if item.get('nombre_avis') is not None else 1

            rows_to_insert.append((
                next_id, place_id, nom, categorie, w_name, w_code, commune,
                adresse, raw_phone, site_web, note, nombre_avis, lat, lon, source
            ))

            new_batch_points.append((lat, lon))
            if norm_phone and len(norm_phone) >= 8:
                new_batch_phones.add(norm_phone)

            next_id += 1
            stats['inserted'] += 1

        print(f"[*] Validation terminée. Prêt à insérer {len(rows_to_insert)} nouvelles fiches.")

        # 5. Insertion atomique dans la base SQLite
        if not dry_run and rows_to_insert:
            print("[+] Début de la transaction SQLite atomique (facilities, FTS5, R-Tree)...")
            try:
                self.con.execute("BEGIN TRANSACTION;")

                # A) Insertion dans `facilities`
                self.cur.executemany("""
                    INSERT INTO facilities (
                        id, place_id, nom, categorie, wilaya, wilaya_code, commune,
                        adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, rows_to_insert)

                # B) Insertion dans `facilities_fts`
                fts_rows = [
                    (r[0], r[2], r[6], r[4], r[3], r[8], r[12], r[13])
                    for r in rows_to_insert
                ]
                self.cur.executemany("""
                    INSERT INTO facilities_fts (rowid, nom, commune, wilaya, categorie, telephone, latitude, longitude)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, fts_rows)

                # C) Insertion dans `facilities_rtree`
                rtree_rows = [
                    (r[0], r[12], r[12], r[13], r[13])
                    for r in rows_to_insert
                ]
                self.cur.executemany("""
                    INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
                    VALUES (?, ?, ?, ?, ?);
                """, rtree_rows)

                self.con.commit()
                print("[V] Transaction SQLite validée avec succès (COMMIT).")

            except Exception as e:
                self.con.rollback()
                print(f"[!] ERREUR lors de l'insertion : {e}. Rollback effectué.")
                raise e

        return stats

    def check_integrity(self) -> str:
        """Exécute PRAGMA integrity_check."""
        self.cur.execute("PRAGMA integrity_check;")
        return self.cur.fetchone()[0]

    def print_breakdown(self):
        """Affiche un tableau récapitulatif du décompte des établissements par wilaya et catégorie."""
        print("\n" + "=" * 78)
        print("         RÉCAPITULATIF DES ÉTABLISSEMENTS PAR WILAYA & CATÉGORIE        ")
        print("=" * 78)

        # Total général
        self.cur.execute("SELECT count(*) FROM facilities;")
        total_all = self.cur.fetchone()[0]

        # Décompte par Wilaya
        self.cur.execute("""
            SELECT wilaya_code, min(wilaya) as w_name, count(*) as cnt
            FROM facilities
            GROUP BY wilaya_code
            ORDER BY CAST(wilaya_code AS INTEGER) ASC;
        """)
        wilaya_rows = self.cur.fetchall()

        print(f"| {'Code':<4} | {'Wilaya':<24} | {'Fiches Totales':<14} |")
        print("|" + "-" * 6 + "|" + "-" * 26 + "|" + "-" * 16 + "|")
        for code, w_name, cnt in wilaya_rows:
            canon_name = WILAYAS_58.get(code, w_name)
            print(f"| {code:<4} | {canon_name:<24} | {cnt:>14} |")

        print("=" * 78)
        print(f"  TOTAL NATIONAL D'ÉTABLISSEMENTS QUALIFIÉS : {total_all}")

        # Décompte par Catégorie
        print("\n  Répartition par grande catégorie :")
        self.cur.execute("""
            SELECT categorie, count(*) as cnt
            FROM facilities
            GROUP BY categorie
            ORDER BY cnt DESC
            LIMIT 15;
        """)
        for cat, cnt in self.cur.fetchall():
            print(f"    - {cat:<32} : {cnt:>6} fiches")
        print("=" * 78 + "\n")

    def close(self):
        self.con.close()

def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Pipeline d'injection de données de santé MEDIZY")
    parser.add_argument('--input', '-i', required=True, help="Chemin du fichier JSON ou CSV à importer")
    parser.add_argument('--db', default='assets/data/sante_dz_bundled.db', help="Chemin de la base de données SQLite")
    parser.add_argument('--dry-run', action='store_true', help="Mode simulation sans écriture en base")
    parser.add_argument('--breakdown', action='store_true', help="Affiche le tableau récapitulatif complet par Wilaya")

    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"Erreur : fichier introuvable : {input_path}")
        sys.exit(1)

    # Chargement des données
    facilities_data = []
    if input_path.endswith('.json'):
        with open(input_path, 'r', encoding='utf-8') as f:
            facilities_data = json.load(f)
    elif input_path.endswith('.csv'):
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            facilities_data = list(reader)
    else:
        print("Erreur : format non supporté. Utilisez un fichier .json ou .csv")
        sys.exit(1)

    injector = HealthFacilityInjector(args.db)
    try:
        stats = injector.inject_dataset(facilities_data, dry_run=args.dry_run)
        integrity = injector.check_integrity()

        print("\n=======================================================")
        print("           RAPPORT D'INGESTION SANITAIRE MEDIZY        ")
        print("=======================================================")
        print(f"  Total fiches reçues             : {stats['total_received']}")
        print(f"  Fiches insérées (Validées)      : {stats['inserted']}")
        print(f"  Rejetées (GPS hors Algérie)     : {stats['rejected_invalid_gps']}")
        print(f"  Rejetées (Doublon téléphone)    : {stats['rejected_duplicate_phone']}")
        print(f"  Rejetées (Doublon prox < 10m)   : {stats['rejected_duplicate_proximity']}")
        print(f"  Rejetées (Nom manquant)         : {stats['rejected_missing_name']}")
        print(f"  Intégrité SQLite (PRAGMA)       : {integrity}")
        print("=======================================================\n")

        if integrity != "ok":
            print("[ATTENTION] Intégrité SQLite anormale !")
            sys.exit(1)

        # Affichage du tableau récapitulatif
        injector.print_breakdown()

    finally:
        injector.close()

if __name__ == '__main__':
    main()
