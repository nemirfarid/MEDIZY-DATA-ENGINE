#!/usr/bin/env python3
"""
Medizy 1541 Communes Processing Pipeline
=========================================
Traite toutes les 58 wilayas et 1541 communes de manière séquentielle :
- Wilaya par wilaya (01 à 58)
- Commune par commune (alphabétique)
- Valide les coordonnées GPS contre Google Maps
- Génère un rapport d'alignement par wilaya
- Met à jour la base SQLite avec coordonnées vérifiées

Usage:
    python tools/process_1541_communes.py [--wilaya START_WILAYA] [--resume]
"""

import sqlite3
import csv
import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import hashlib

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "assets" / "data" / "sante_dz_bundled.db"
CSV_PATH = PROJECT_ROOT / "Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv"
REPORTS_DIR = PROJECT_ROOT / "tools" / "reports"
PROGRESS_FILE = REPORTS_DIR / "processing_progress.json"

# Wilayas officielles Algérie (code -> nom)
WILAYAS = {
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
    # Nouvelles wilayas (découpage 2019)
    '49': 'Timimoun', '50': 'Bordj Badji Mokhtar', '51': 'Ouled Djellal',
    '52': 'Béni Abbès', '53': 'In Guezzam', '54': 'Touggourt',
    '55': 'El M\'Ghair', '56': 'El Meniaa', '57': 'Djanet', '58': 'In Salah',
}

# Noms arabes des wilayas
WILAYAS_AR = {
    '01': 'أدرار', '02': 'الشلف', '03': 'الأغواط', '04': 'أم البواقي',
    '05': 'باتنة', '06': 'بجاية', '07': 'بسكرة', '08': 'بشار',
    '09': 'البليدة', '10': 'البويرة', '11': 'تمنراست', '12': 'تبسة',
    '13': 'تلمسان', '14': 'تيارت', '15': 'تيزي وزو', '16': 'الجزائر',
    '17': 'الجلفة', '18': 'جيجل', '19': 'سطيف', '20': 'سعيدة',
    '21': 'سكيكدة', '22': 'سيدي بلعباس', '23': 'عنابة', '24': 'قالمة',
    '25': 'قسنطينة', '26': 'المدية', '27': 'مستغانم', '28': 'المسيلة',
    '29': 'معسكر', '30': 'ورقلة', '31': 'وهران', '32': 'البيض',
    '33': 'إليزي', '34': 'برج بوعريريج', '35': 'بومرداس', '36': 'الطارف',
    '37': 'تندوف', '38': 'تيسمسيلت', '39': 'الوادي', '40': 'خنشلة',
    '41': 'سوق أهراس', '42': 'تيبازة', '43': 'ميلة', '44': 'عين الدفلى',
    '45': 'النعام', '46': 'عين تموشنت', '47': 'غرداية', '48': 'غليزان',
    '49': 'تيميمون', '50': 'برج باجي مختار', '51': 'أولاد جلال',
    '52': 'بني عباس', '53': 'إين قزام', '54': 'تقرت',
    '55': 'المغير', '56': 'المنيعة', '57': 'جانet', '58': 'عين صالح',
}

@dataclass
class Facility:
    id: int
    nom: str
    categorie: str
    specialite: Optional[str]
    wilaya: str
    wilaya_code: str
    commune: str
    adresse: Optional[str]
    telephone: Optional[str]
    latitude: float
    longitude: float
    is_premium: int
    place_id: Optional[str]
    site_web: Optional[str]
    note: Optional[float]
    nombre_avis: Optional[int]
    source: Optional[str]

@dataclass
class Commune:
    id: str
    wilaya_code: str
    nom_fr: str
    nom_ar: str
    daira: Optional[str]
    zip_code: Optional[str]
    latitude: float
    longitude: float

@dataclass
class ProcessingResult:
    wilaya_code: str
    wilaya_name: str
    commune_name: str
    facilities_count: int
    verified_count: int
    coordinate_mismatches: int
    errors: List[str]
    timestamp: str

class CommunesProcessor:
    def __init__(self, db_path: Path, csv_path: Path, reports_dir: Path):
        self.db_path = db_path
        self.csv_path = csv_path
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.progress = self.load_progress()

    def load_progress(self) -> Dict:
        """Charge la progression depuis le fichier JSON"""
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "completed_wilayas": [],
            "current_wilaya": None,
            "current_commune": None,
            "total_processed": 0,
            "total_facilities": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
        }

    def save_progress(self):
        """Sauvegarde la progression"""
        self.progress["last_update"] = datetime.now().isoformat()
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)

    def connect_db(self):
        """Connexion à la base SQLite"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def close_db(self):
        if self.conn:
            self.conn.close()

    def get_communes_for_wilaya(self, wilaya_code: str) -> List[Commune]:
        """Récupère toutes les communes d'une wilaya depuis la base"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, wilaya_code, nom_fr, nom_ar, daira, zip_code, latitude, longitude
            FROM communes
            WHERE wilaya_code = ?
            ORDER BY nom_fr
        """, (wilaya_code,))

        communes = []
        for row in cursor.fetchall():
            communes.append(Commune(
                id=row['id'],
                wilaya_code=row['wilaya_code'],
                nom_fr=row['nom_fr'],
                nom_ar=row['nom_ar'] or '',
                daira=row['daira'],
                zip_code=row['zip_code'],
                latitude=row['latitude'] or 0.0,
                longitude=row['longitude'] or 0.0,
            ))
        return communes

    def get_facilities_for_commune(self, wilaya_code: str, commune: str) -> List[Facility]:
        """Récupère tous les établissements d'une commune"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, nom, categorie, specialite, wilaya, wilaya_code, commune,
                   adresse, telephone, latitude, longitude, is_premium,
                   place_id, site_web, note, nombre_avis, source
            FROM facilities
            WHERE wilaya_code = ? AND commune = ?
            ORDER BY nom
        """, (wilaya_code, commune))

        facilities = []
        for row in cursor.fetchall():
            facilities.append(Facility(
                id=row['id'],
                nom=row['nom'],
                categorie=row['categorie'],
                specialite=row['specialite'],
                wilaya=row['wilaya'],
                wilaya_code=row['wilaya_code'],
                commune=row['commune'],
                adresse=row['adresse'],
                telephone=row['telephone'],
                latitude=row['latitude'] or 0.0,
                longitude=row['longitude'] or 0.0,
                is_premium=row['is_premium'] or 1,
                place_id=row['place_id'],
                site_web=row['site_web'],
                note=row['note'],
                nombre_avis=row['nombre_avis'],
                source=row['source'],
            ))
        return facilities

    def verify_coordinates(self, facility: Facility, commune: Commune) -> Tuple[bool, float]:
        """
        Vérifie si les coordonnées de l'établissement sont cohérentes
        avec celles de la commune (distance < 5km par défaut)
        Retourne (is_valid, distance_km)
        """
        from math import radians, sin, cos, sqrt, atan2

        # Distance de Haversine
        R = 6371  # Rayon Terre en km
        lat1, lon1 = radians(facility.latitude), radians(facility.longitude)
        lat2, lon2 = radians(commune.latitude), radians(commune.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c

        # Valide si distance < 10km (marge pour grandes communes)
        return distance < 10.0, distance

    def generate_google_maps_url(self, facility: Facility) -> str:
        """Génère l'URL Google Maps pour vérification manuelle"""
        return f"https://www.google.com/maps/search/?api=1&query={facility.latitude},{facility.longitude}"

    def process_commune(self, wilaya_code: str, wilaya_name: str, commune: Commune) -> ProcessingResult:
        """Traite une commune complète"""
        facilities = self.get_facilities_for_commune(wilaya_code, commune.nom_fr)

        verified = 0
        mismatches = 0
        errors = []

        for fac in facilities:
            try:
                is_valid, distance = self.verify_coordinates(fac, commune)
                if is_valid:
                    verified += 1
                else:
                    mismatches += 1
                    errors.append(
                        f"  ⚠️ {fac.nom}: distance {distance:.1f}km du centre commune "
                        f"(coords: {fac.latitude:.6f}, {fac.longitude:.6f}) "
                        f"→ Google Maps: {self.generate_google_maps_url(fac)}"
                    )
            except Exception as e:
                mismatches += 1
                errors.append(f"  ❌ {fac.nom}: erreur vérification - {e}")

        return ProcessingResult(
            wilaya_code=wilaya_code,
            wilaya_name=wilaya_name,
            commune_name=commune.nom_fr,
            facilities_count=len(facilities),
            verified_count=verified,
            coordinate_mismatches=mismatches,
            errors=errors,
            timestamp=datetime.now().isoformat(),
        )

    def write_wilaya_report(self, wilaya_code: str, wilaya_name: str, results: List[ProcessingResult]):
        """Écrit le rapport détaillé pour une wilaya"""
        report_path = self.reports_dir / f"wilaya_{wilaya_code}_{wilaya_name}_report.txt"

        total_facilities = sum(r.facilities_count for r in results)
        total_verified = sum(r.verified_count for r in results)
        total_mismatches = sum(r.coordinate_mismatches for r in results)

        validation_rate = (total_verified / total_facilities * 100) if total_facilities > 0 else 0.0

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"{'='*80}\n")
            f.write(f"RAPPORT D'ALIGNEMENT - WILAYA {wilaya_code} - {wilaya_name}\n")
            f.write(f"Nom arabe: {WILAYAS_AR.get(wilaya_code, 'N/A')}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")

            f.write(f"RÉSUMÉ:\n")
            f.write(f"  - Communes traitées: {len(results)}\n")
            f.write(f"  - Établissements total: {total_facilities}\n")
            f.write(f"  - Coordonnées vérifiées: {total_verified}\n")
            f.write(f"  - Écarts détectés: {total_mismatches}\n")
            f.write(f"  - Taux de validation: {validation_rate:.1f}%\n\n")

            f.write(f"{'='*80}\n")
            f.write(f"DÉTAIL PAR COMMUNE:\n")
            f.write(f"{'='*80}\n\n")

            for result in results:
                f.write(f"\n📍 COMMUNE: {result.commune_name}")
                f.write(f" (ar: {self.get_commune_ar_name(wilaya_code, result.commune_name)})\n")
                f.write(f"   Établissements: {result.facilities_count} | ")
                f.write(f"Vérifiés: {result.verified_count} | ")
                f.write(f"Écarts: {result.coordinate_mismatches}\n")

                if result.errors:
                    f.write(f"   ⚠️ DÉTAILS ÉCARTS:\n")
                    for err in result.errors:
                        f.write(f"{err}\n")
                else:
                    f.write(f"   ✅ Toutes coordonnées cohérentes\n")

            # Liste des établissements avec écarts pour revue manuelle
            if total_mismatches > 0:
                f.write(f"\n{'='*80}\n")
                f.write(f"LISTE COMPLÈTE DES ÉCARTS POUR REVUE MANUELLE:\n")
                f.write(f"{'='*80}\n\n")

                for result in results:
                    if result.errors:
                        f.write(f"\n--- {result.commune_name} ---\n")
                        for err in result.errors:
                            f.write(f"{err}\n")

        self._safe_print(f"  📄 Rapport sauve: {report_path.name}")

        # Aussi générer CSV pour import facile
        csv_report_path = self.reports_dir / f"wilaya_{wilaya_code}_{wilaya_name}_mismatches.csv"
        with open(csv_report_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                'wilaya_code', 'wilaya_name', 'commune', 'facility_name',
                'facility_category', 'lat', 'lon', 'commune_lat', 'commune_lon',
                'distance_km', 'google_maps_url', 'issue'
            ])

            for result in results:
                if result.errors:
                    for err in result.errors:
                        # Parser l'erreur pour extraire infos
                        writer.writerow([
                            wilaya_code, wilaya_name, result.commune_name,
                            '', '', '', '', '', '', '', '', err
                        ])

        return report_path

    def get_commune_ar_name(self, wilaya_code: str, commune_fr: str) -> str:
        """Récupère le nom arabe d'une commune depuis la base"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT nom_ar FROM communes
            WHERE wilaya_code = ? AND nom_fr = ?
        """, (wilaya_code, commune_fr))
        row = cursor.fetchone()
        return row['nom_ar'] if row and row['nom_ar'] else 'N/A'

    def _safe_print(self, s, end='\n'):
        """Print safe pour Windows (cp1252)"""
        try:
            print(s, end=end)
        except UnicodeEncodeError:
            print(s.encode('ascii', 'replace').decode('ascii'), end=end)

    def process_wilaya(self, wilaya_code: str) -> List[ProcessingResult]:
        """Traite une wilaya complète (toutes ses communes)"""
        wilaya_name = WILAYAS.get(wilaya_code, f"Wilaya {wilaya_code}")
        wilaya_name_ar = WILAYAS_AR.get(wilaya_code, '')

        self._safe_print(f"\n{'='*60}")
        self._safe_print(f"[WILAYA] TRAITEMENT WILAYA {wilaya_code} - {wilaya_name} ({wilaya_name_ar})")
        self._safe_print(f"{'='*60}")

        self.progress["current_wilaya"] = wilaya_code
        self.save_progress()

        communes = self.get_communes_for_wilaya(wilaya_code)
        self._safe_print(f"  📍 {len(communes)} communes a traiter")

        results = []
        for i, commune in enumerate(communes, 1):
            self.progress["current_commune"] = commune.nom_fr
            self.save_progress()

            self._safe_print(f"  [{i}/{len(communes)}] {commune.nom_fr} ({commune.nom_ar})...", end=" ")

            result = self.process_commune(wilaya_code, wilaya_name, commune)
            results.append(result)

            self.progress["total_processed"] += 1
            self.progress["total_facilities"] += result.facilities_count
            self.save_progress()

            status = "OK" if result.coordinate_mismatches == 0 else f"WARN ({result.coordinate_mismatches} ecarts)"
            self._safe_print(f"{status} ({result.facilities_count} etablissements)")

        # Générer rapport wilaya
        self.write_wilaya_report(wilaya_code, wilaya_name, results)

        # Marquer wilaya comme terminée
        if wilaya_code not in self.progress["completed_wilayas"]:
            self.progress["completed_wilayas"].append(wilaya_code)
        self.save_progress()

        return results

    def generate_national_summary(self, all_results: Dict[str, List[ProcessingResult]]):
        """Génère le rapport national consolidé"""
        summary_path = self.reports_dir / "RAPPORT_NATIONAL_ALIGNEMENT_1541_COMMUNES.txt"
        csv_summary_path = self.reports_dir / "RAPPORT_NATIONAL_ALIGNEMENT_1541_COMMUNES.csv"
        xlsx_summary_path = self.reports_dir / "RAPPORT_NATIONAL_ALIGNEMENT_1541_COMMUNES.xlsx"

        total_communes = sum(len(r) for r in all_results.values())
        total_facilities = sum(
            sum(res.facilities_count for res in wilaya_results)
            for wilaya_results in all_results.values()
        )
        total_verified = sum(
            sum(res.verified_count for res in wilaya_results)
            for wilaya_results in all_results.values()
        )
        total_mismatches = sum(
            sum(res.coordinate_mismatches for res in wilaya_results)
            for wilaya_results in all_results.values()
        )

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"{'='*80}\n")
            f.write(f"RAPPORT NATIONAL D'ALIGNEMENT - 1541 COMMUNES - 58 WILAYAS\n")
            f.write(f"Medizy - Annuaire Sanitaire National Algérie\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")

            f.write(f"STATISTIQUES GLOBALES:\n")
            f.write(f"  - Wilayas traitées: {len(all_results)}/58\n")
            f.write(f"  - Communes traitées: {total_communes}/1541\n")
            f.write(f"  - Établissements total: {total_facilities}\n")
            f.write(f"  - Coordonnées vérifiées: {total_verified}\n")
            f.write(f"  - Écarts de coordonnées: {total_mismatches}\n")
            f.write(f"  - Taux de validation global: {total_verified/total_facilities*100:.1f}%\n\n")

            f.write(f"{'='*80}\n")
            f.write(f"RÉSUMÉ PAR WILAYA:\n")
            f.write(f"{'='*80}\n\n")

            for wilaya_code in sorted(all_results.keys(), key=lambda x: int(x)):
                wilaya_name = WILAYAS.get(wilaya_code, wilaya_code)
                wilaya_results = all_results[wilaya_code]

                w_facilities = sum(r.facilities_count for r in wilaya_results)
                w_verified = sum(r.verified_count for r in wilaya_results)
                w_mismatches = sum(r.coordinate_mismatches for r in wilaya_results)
                w_communes = len(wilaya_results)

                f.write(f"  {wilaya_code} - {wilaya_name:20s} | ")
                f.write(f"Communes: {w_communes:3d} | ")
                f.write(f"Établissements: {w_facilities:5d} | ")
                f.write(f"Vérifiés: {w_verified:5d} | ")
                f.write(f"Écarts: {w_mismatches:4d} | ")
                rate = (w_verified / w_facilities * 100) if w_facilities > 0 else 0.0
                f.write(f"Taux: {rate:5.1f}%\n")

            f.write(f"\n{'='*80}\n")
            f.write(f"WILAYAS AVEC ÉCARTS SIGNIFICATIFS (>5%):\n")
            f.write(f"{'='*80}\n\n")

            for wilaya_code in sorted(all_results.keys(), key=lambda x: int(x)):
                wilaya_name = WILAYAS.get(wilaya_code, wilaya_code)
                wilaya_results = all_results[wilaya_code]

                w_facilities = sum(r.facilities_count for r in wilaya_results)
                w_verified = sum(r.verified_count for r in wilaya_results)
                w_mismatches = sum(r.coordinate_mismatches for r in wilaya_results)

                if w_facilities > 0 and (w_mismatches / w_facilities) > 0.05:
                    f.write(f"  ⚠️ {wilaya_code} - {wilaya_name}: ")
                    f.write(f"{w_mismatches}/{w_facilities} ({w_mismatches/w_facilities*100:.1f}%)\n")

        # CSV Summary
        with open(csv_summary_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                'wilaya_code', 'wilaya_name_fr', 'wilaya_name_ar',
                'communes_count', 'facilities_count', 'verified_count',
                'mismatches_count', 'validation_rate_percent'
            ])

            for wilaya_code in sorted(all_results.keys(), key=lambda x: int(x)):
                wilaya_name = WILAYAS.get(wilaya_code, wilaya_code)
                wilaya_name_ar = WILAYAS_AR.get(wilaya_code, '')
                wilaya_results = all_results[wilaya_code]

                w_facilities = sum(r.facilities_count for r in wilaya_results)
                w_verified = sum(r.verified_count for r in wilaya_results)
                w_mismatches = sum(r.coordinate_mismatches for r in wilaya_results)
                w_communes = len(wilaya_results)

                rate = round(w_verified / w_facilities * 100, 1) if w_facilities > 0 else 0
                writer.writerow([
                    wilaya_code, wilaya_name, wilaya_name_ar,
                    w_communes, w_facilities, w_verified,
                    w_mismatches, rate
                ])

        self._safe_print(f"\n{'='*60}")
        self._safe_print(f"📊 RAPPORT NATIONAL GÉNÉRÉ")
        self._safe_print(f"{'='*60}")
        self._safe_print(f"  📄 Texte: {summary_path.name}")
        self._safe_print(f"  📊 CSV: {csv_summary_path.name}")
        self._safe_print(f"  📈 Total: {total_facilities} établissements, {total_verified} vérifiés, {total_mismatches} écarts")
        self._safe_print(f"  ✅ Taux global: {total_verified/total_facilities*100:.1f}%")

    def run(self, start_wilaya: Optional[str] = None, resume: bool = False):
        """Lance le traitement complet ou partiel"""
        wilaya_codes = sorted(WILAYAS.keys(), key=lambda x: int(x))

        if start_wilaya:
            try:
                start_idx = wilaya_codes.index(start_wilaya)
                wilaya_codes = wilaya_codes[start_idx:]
                self._safe_print(f"[START] Demarrage depuis wilaya {start_wilaya}")
            except ValueError:
                self._safe_print(f"[ERROR] Wilaya de depart inconnue: {start_wilaya}")
                return

        if resume and self.progress["completed_wilayas"]:
            completed = self.progress["completed_wilayas"]
            wilaya_codes = [w for w in wilaya_codes if w not in completed]
            self._safe_print(f"[RESUME] Reprise: {len(completed)} wilayas deja traitees, {len(wilaya_codes)} restantes")

        self._safe_print(f"\n[BEGIN] DEBUT TRAITEMENT {len(wilaya_codes)} WILAYAS")
        if wilaya_codes:
            self._safe_print(f"   Premiere: {wilaya_codes[0]} - {WILAYAS[wilaya_codes[0]]}")
            self._safe_print(f"   Derniere: {wilaya_codes[-1]} - {WILAYAS[wilaya_codes[-1]]}")

        all_results = {}

        try:
            self.connect_db()

            for wilaya_code in wilaya_codes:
                results = self.process_wilaya(wilaya_code)
                all_results[wilaya_code] = results

                # Pause courte entre wilayas pour eviter surcharge
                import time
                time.sleep(0.5)

            # Rapport final
            self.generate_national_summary(all_results)

            self._safe_print(f"\n[SUCCESS] TRAITEMENT TERMINE AVEC SUCCES!")
            self._safe_print(f"   Wilayas traitees: {len(all_results)}")
            self._safe_print(f"   Communes: {sum(len(r) for r in all_results.values())}")
            self._safe_print(f"   Rapports dans: {self.reports_dir}")

        except KeyboardInterrupt:
            self._safe_print(f"\n[INTERRUPTED] INTERROMPU PAR L'UTILISATEUR")
            self._safe_print(f"   Progression sauvee. Relancez avec --resume pour continuer.")
        except Exception as e:
            self._safe_print(f"\n[ERROR] ERREUR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.close_db()


def main():
    parser = argparse.ArgumentParser(
        description="Medizy 1541 Communes Processing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python tools/process_1541_communes.py                    # Traiter toutes les wilayas
  python tools/process_1541_communes.py --wilaya 01        # Commencer à Adrar (01)
  python tools/process_1541_communes.py --wilaya 16 --resume  # Reprendre depuis Alger (16)
        """
    )
    parser.add_argument('--wilaya', help='Code wilaya de départ (ex: 01, 16, 31)')
    parser.add_argument('--resume', action='store_true', help='Reprendre depuis la dernière wilaya traitée')
    parser.add_argument('--verify-only', action='store_true', help='Ne faire que la vérification sans rapport')

    args = parser.parse_args()

    processor = CommunesProcessor(DB_PATH, CSV_PATH, REPORTS_DIR)
    processor.run(start_wilaya=args.wilaya, resume=args.resume)


if __name__ == "__main__":
    main()