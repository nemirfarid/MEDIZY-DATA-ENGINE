#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Moteur de recherche et de requêtes géospatiales (Phase 9)
=============================================================================
Module optimisé de recherche plein texte, facettes et requêtes spatiales
pour les 23 669 établissements de santé des 58 wilayas d'Algérie.

Caractéristiques :
- Connexion SQLite en lecture seule stricte (mode=ro) pour protéger la base de prod.
- Exploitation des index existants (wilaya, commune, categorie_recherche, latlng).
- Fonction SQL native `haversine()` injectée à la connexion pour calcul et tri direct C/SQLite.
- Pré-filtrage spatial ultra-rapide par Bounding Box (index B-Tree `idx_places_latlng`).
- Recherche plein texte multi-champs (nom, catégorie, adresse, commune).
- Résolution intelligente des 58 wilayas (par code officiel 01-58 ou par nom).
- Intégration de la taxonomie médicale (synonymes et variantes).
- Pagination, facettes et métriques de temps d'exécution (ms).
"""

import math
import os
import sqlite3
import time
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

# Référence officielle des 58 wilayas d'Algérie
OFFICIAL_WILAYAS: List[Tuple[str, str]] = [
    ("01", "Adrar"), ("02", "Chlef"), ("03", "Laghouat"), ("04", "Oum El Bouaghi"), ("05", "Batna"),
    ("06", "Béjaïa"), ("07", "Biskra"), ("08", "Béchar"), ("09", "Blida"), ("10", "Bouira"),
    ("11", "Tamanrasset"), ("12", "Tébessa"), ("13", "Tlemcen"), ("14", "Tiaret"), ("15", "Tizi Ouzou"),
    ("16", "Alger"), ("17", "Djelfa"), ("18", "Jijel"), ("19", "Sétif"), ("20", "Saïda"),
    ("21", "Skikda"), ("22", "Sidi Bel Abbès"), ("23", "Annaba"), ("24", "Guelma"), ("25", "Constantine"),
    ("26", "Médéa"), ("27", "Mostaganem"), ("28", "M'Sila"), ("29", "Mascara"), ("30", "Ouargla"),
    ("31", "Oran"), ("32", "El Bayadh"), ("33", "Illizi"), ("34", "Bordj Bou Arréridj"), ("35", "Boumerdès"),
    ("36", "El Tarf"), ("37", "Tindouf"), ("38", "Tissemsilt"), ("39", "El Oued"), ("40", "Khenchela"),
    ("41", "Souk Ahras"), ("42", "Tipaza"), ("43", "Mila"), ("44", "Aïn Defla"), ("45", "Naâma"),
    ("46", "Aïn Témouchent"), ("47", "Ghardaïa"), ("48", "Relizane"), ("49", "Timimoun"),
    ("50", "Bordj Badji Mokhtar"), ("51", "Ouled Djellal"), ("52", "Béni Abbès"), ("53", "In Salah"),
    ("54", "In Guezzam"), ("55", "Touggourt"), ("56", "Djanet"), ("57", "El Meghaier"), ("58", "El Meniaa")
]


def strip_accents(text: str) -> str:
    """Supprime les accents et normalise la casse d'une chaîne de caractères."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)]).lower().strip()


# Précalcul des tables de correspondance pour les wilayas
WILAYA_BY_CODE: Dict[str, str] = {code: name for code, name in OFFICIAL_WILAYAS}
WILAYA_BY_NORM_NAME: Dict[str, str] = {strip_accents(name): name for _, name in OFFICIAL_WILAYAS}
for _, name in OFFICIAL_WILAYAS:
    cleaned = strip_accents(name).replace("-", " ").replace("'", " ")
    WILAYA_BY_NORM_NAME[cleaned] = name


# Dictionnaire des synonymes médicaux courants
MEDICAL_SYNONYMS: Dict[str, List[str]] = {
    "cardio": ["cardiologue", "cardiologie", "cabinet cardiologie"],
    "cardiologue": ["cardiologue", "cardiologie", "cabinet cardiologie"],
    "dentiste": ["dentiste", "cabinet dentaire", "chirurgien dentiste"],
    "dentaire": ["cabinet dentaire", "dentiste"],
    "generaliste": ["médecin", "médecin généraliste", "cabinet médical"],
    "medecin": ["médecin", "cabinet médical", "médecin généraliste", "médecin spécialiste"],
    "dermato": ["dermatologue", "dermatologie", "cabinet dermatologie"],
    "dermatologue": ["dermatologue", "dermatologie"],
    "ophtalmo": ["ophtalmologue", "ophtalmologie", "cabinet ophtalmologie"],
    "ophtalmologue": ["ophtalmologue", "ophtalmologie"],
    "pediatre": ["pédiatre", "pédiatrie", "cabinet pédiatrie"],
    "gyneco": ["gynécologue", "gynécologie", "cabinet gynécologie"],
    "gynecologue": ["gynécologue", "gynécologie", "cabinet gynécologie"],
    "pharmacie": ["pharmacie", "officine"],
    "labo": ["laboratoire", "laboratoire médical", "laboratoire d'analyse médicale"],
    "laboratoire": ["laboratoire", "laboratoire médical", "laboratoire d'analyse médicale"],
    "hopital": ["hôpital", "centre hospitalier", "eph", "chu", "ehs"],
    "clinique": ["clinique", "clinique médico-chirurgicale", "polyclinique"],
    "radio": ["radiologue", "radiologie", "imagerie", "centre d'imagerie médicale"],
    "scanner": ["radiologue", "radiologie", "imagerie", "centre d'imagerie médicale"],
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance géodésique en kilomètres entre deux points
    via la formule de Haversine.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999999.0
    r = 6371.0088  # Rayon moyen de la Terre en km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


@dataclass
class FacilityRecord:
    id: int
    place_id: Optional[str]
    nom: str
    categorie_recherche: Optional[str]
    wilaya: Optional[str]
    commune: Optional[str]
    adresse: Optional[str]
    telephone: Optional[str]
    telephone_normalized: Optional[str]
    site_web: Optional[str]
    note: Optional[str]
    nombre_avis: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    google_maps_url: Optional[str]
    source: Optional[str]
    distance_km: Optional[float] = None


@dataclass
class SearchResult:
    total_count: int
    page: int
    limit: int
    results: List[Dict[str, Any]]
    execution_time_ms: float
    filters_applied: Dict[str, Any]


class MedizySearchEngine:
    """Moteur de recherche géospatiale et plein texte Medizy ultra-performant."""

    def __init__(self, db_path: Optional[str] = None):
        target = db_path or os.environ.get("MEDIZY_DB_PATH") or r"C:\SANTE_DZ_SCRAPER\medizy_scraper.db"
        self.db_path = os.path.abspath(target)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Base de données introuvable : {self.db_path}")
        import threading
        self._local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        """Ouvre et réutilise une connexion par thread en lecture seule stricte."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.execute("SELECT 1;")
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                conn = None
                self._local.conn = None

        if conn is None:
            uri = f"file:{self.db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Optimisations lecture seule : cache mémoire et mmap
            conn.execute("PRAGMA cache_size = -16000;")
            conn.execute("PRAGMA mmap_size = 67108864;")
            conn.create_function("haversine", 4, haversine_distance)
            self._local.conn = conn
        return conn

    def close(self):
        """Ferme la connexion du thread courant."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    @staticmethod
    def resolve_wilaya(wilaya_input: Optional[str]) -> Optional[str]:
        """
        Résout une chaîne ou code de wilaya vers son nom canonique officiel.
        Exemples: "16" -> "Alger", "oran" -> "Oran", "setif" -> "Sétif"
        """
        if not wilaya_input:
            return None
        clean_input = str(wilaya_input).strip()

        # Code numérique à 1 ou 2 chiffres
        if clean_input.isdigit():
            code = clean_input.zfill(2)
            return WILAYA_BY_CODE.get(code)

        # Recherche par nom normalisé
        norm = strip_accents(clean_input)
        if norm in WILAYA_BY_NORM_NAME:
            return WILAYA_BY_NORM_NAME[norm]

        norm_spaces = norm.replace("-", " ").replace("'", " ")
        if norm_spaces in WILAYA_BY_NORM_NAME:
            return WILAYA_BY_NORM_NAME[norm_spaces]

        return clean_input

    def search(
        self,
        query: Optional[str] = None,
        wilaya: Optional[str] = None,
        commune: Optional[str] = None,
        specialite: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 10.0,
        has_phone: Optional[bool] = None,
        source: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResult:
        """
        Exécute une recherche combinée ultra-rapide (texte, facettes administratives, proximité GPS).
        Exploite directement les index existants :
        - idx_places_wilaya (SEARCH)
        - idx_places_commune (SEARCH)
        - idx_places_category (SEARCH / IN)
        - idx_places_latlng (SEARCH Bounding Box)
        """
        t0 = time.perf_counter()
        conn = self._get_connection()
        cur = conn.cursor()

        where_clauses: List[str] = []
        params: List[Any] = []
        filters_applied: Dict[str, Any] = {}

        # 1. Filtre Wilaya
        resolved_wilaya = self.resolve_wilaya(wilaya)
        if resolved_wilaya:
            where_clauses.append("wilaya = ?")
            params.append(resolved_wilaya)
            filters_applied["wilaya"] = resolved_wilaya

        # 2. Filtre Commune
        if commune and commune.strip():
            clean_com = commune.strip()
            where_clauses.append("commune LIKE ?")
            params.append(f"%{clean_com}%")
            filters_applied["commune"] = clean_com

        # 3. Filtre Spécialité / Catégorie
        if specialite and specialite.strip():
            spec_clean = specialite.strip()
            spec_norm = strip_accents(spec_clean)
            synonyms = MEDICAL_SYNONYMS.get(spec_norm, [spec_clean])
            
            cat_clauses = ["categorie_recherche LIKE ?" for _ in synonyms]
            where_clauses.append(f"({' OR '.join(cat_clauses)})")
            for syn in synonyms:
                params.append(f"%{syn}%")
            filters_applied["specialite"] = spec_clean

        # 4. Filtre Téléphone
        if has_phone is True:
            where_clauses.append("telephone IS NOT NULL AND TRIM(telephone) != ''")
            filters_applied["has_phone"] = True

        # 5. Filtre Source
        if source and source.strip():
            where_clauses.append("source LIKE ?")
            params.append(source.strip())
            filters_applied["source"] = source.strip()

        # 6. Recherche plein texte multi-champs
        if query and query.strip():
            q_clean = query.strip()
            tokens = q_clean.split()
            token_clauses = []
            for tok in tokens:
                tok_norm = strip_accents(tok)
                tok_syns = MEDICAL_SYNONYMS.get(tok_norm, [tok])
                sub_or = []
                for s in tok_syns:
                    sub_or.append("(nom LIKE ? OR categorie_recherche LIKE ? OR adresse LIKE ? OR commune LIKE ?)")
                    p = f"%{s}%"
                    params.extend([p, p, p, p])
                token_clauses.append(f"({' OR '.join(sub_or)})")
            where_clauses.append(f"({' AND '.join(token_clauses)})")
            filters_applied["query"] = q_clean

        # 7. Pré-filtrage spatial par Bounding Box + Haversine
        geo_mode = (latitude is not None and longitude is not None and radius_km > 0)
        
        if geo_mode:
            filters_applied["geo_center"] = {
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km
            }
            # Calcul du Bounding Box pour déclencher l'index idx_places_latlng
            delta_lat = radius_km / 111.0
            rad_lat = math.radians(latitude)
            cos_lat = max(math.cos(rad_lat), 0.1)
            delta_lon = radius_km / (111.0 * cos_lat)

            min_lat = latitude - delta_lat
            max_lat = latitude + delta_lat
            min_lon = longitude - delta_lon
            max_lon = longitude + delta_lon

            where_clauses.append("latitude BETWEEN ? AND ?")
            params.extend([min_lat, max_lat])
            where_clauses.append("longitude BETWEEN ? AND ?")
            params.extend([min_lon, max_lon])

            # Filtre strict sur la distance géodésique
            where_clauses.append("haversine(?, ?, latitude, longitude) <= ?")
            params.extend([latitude, longitude, radius_km])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Requête de comptage
        count_sql = f"SELECT COUNT(*) FROM places {where_sql}"
        cur.execute(count_sql, params)
        total_count = cur.fetchone()[0]

        select_cols = """
            id, place_id, nom, categorie_recherche, wilaya, commune,
            adresse, telephone, telephone_normalized, site_web, note,
            nombre_avis, latitude, longitude, google_maps_url, source
        """

        if geo_mode:
            # En mode géo : sélection de la distance calculée et tri ascendant par distance
            geo_select = f"{select_cols}, ROUND(haversine(?, ?, latitude, longitude), 3) AS distance_km"
            sql = f"""
                SELECT {geo_select}
                FROM places
                {where_sql}
                ORDER BY distance_km ASC
                LIMIT ? OFFSET ?
            """
            exec_params = [latitude, longitude] + params + [limit, offset]
        else:
            sql = f"""
                SELECT {select_cols}
                FROM places
                {where_sql}
                ORDER BY id ASC
                LIMIT ? OFFSET ?
            """
            exec_params = params + [limit, offset]

        cur.execute(sql, exec_params)
        rows = cur.fetchall()

        results = []
        for row in rows:
            dist = row["distance_km"] if geo_mode and "distance_km" in row.keys() else None
            rec = FacilityRecord(
                id=row["id"],
                place_id=row["place_id"],
                nom=row["nom"],
                categorie_recherche=row["categorie_recherche"],
                wilaya=row["wilaya"],
                commune=row["commune"],
                adresse=row["adresse"],
                telephone=row["telephone"],
                telephone_normalized=row["telephone_normalized"],
                site_web=row["site_web"],
                note=row["note"],
                nombre_avis=row["nombre_avis"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                google_maps_url=row["google_maps_url"],
                source=row["source"],
                distance_km=dist
            )
            results.append(asdict(rec))

        cur.close()
        t1 = time.perf_counter()
        elapsed_ms = round((t1 - t0) * 1000.0, 2)
        page_num = (offset // limit) + 1 if limit > 0 else 1

        return SearchResult(
            total_count=total_count,
            page=page_num,
            limit=limit,
            results=results,
            execution_time_ms=elapsed_ms,
            filters_applied=filters_applied
        )

    def get_place_by_id(self, place_id_or_db_id: Any) -> Optional[Dict[str, Any]]:
        """Récupère un établissement par son place_id ou son id SQLite."""
        conn = self._get_connection()
        cur = conn.cursor()
        if isinstance(place_id_or_db_id, int) or (isinstance(place_id_or_db_id, str) and str(place_id_or_db_id).isdigit()):
            cur.execute("SELECT * FROM places WHERE id = ?", (int(place_id_or_db_id),))
        else:
            cur.execute("SELECT * FROM places WHERE place_id = ?", (str(place_id_or_db_id),))
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return dict(row)

    def get_wilayas_stats(self) -> List[Dict[str, Any]]:
        """Retourne la liste des wilayas couvertes avec le nombre d'établissements."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT wilaya, COUNT(*) as total_facilities,
                   COUNT(CASE WHEN telephone IS NOT NULL AND TRIM(telephone) != '' THEN 1 END) as with_phone
            FROM places
            WHERE wilaya IS NOT NULL AND wilaya != ''
            GROUP BY wilaya
            ORDER BY total_facilities DESC;
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows

    def get_communes_stats(self, wilaya: str) -> List[Dict[str, Any]]:
        """Retourne la liste des communes d'une wilaya avec le nombre d'établissements."""
        resolved = self.resolve_wilaya(wilaya)
        target = resolved if resolved else wilaya
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT commune, COUNT(*) as total_facilities
            FROM places
            WHERE wilaya = ? AND commune IS NOT NULL AND commune != ''
            GROUP BY commune
            ORDER BY total_facilities DESC;
        """, (target,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows

    def get_categories_stats(self) -> List[Dict[str, Any]]:
        """Retourne les catégories / spécialités avec les comptes d'établissements."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT categorie_recherche, COUNT(*) as total
            FROM places
            WHERE categorie_recherche IS NOT NULL AND categorie_recherche != ''
            GROUP BY categorie_recherche
            ORDER BY total DESC;
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows


if __name__ == "__main__":
    engine = MedizySearchEngine()
    print("Test du moteur de recherche Medizy (Phase 9)...")
    
    # 1. Test Wilaya par code '16' (Alger)
    res_wil = engine.search(wilaya="16", limit=5)
    print(f"\n[Wilaya '16'] Trouvés: {res_wil.total_count:,} en {res_wil.execution_time_ms} ms")
    for r in res_wil.results[:3]:
        print(f"  - {r['nom']} ({r['categorie_recherche']}) - {r['commune']}, {r['wilaya']}")

    # 2. Test Spécialité + Wilaya
    res_spec = engine.search(wilaya="Oran", specialite="cardio", limit=5)
    print(f"\n[Oran + cardio] Trouvés: {res_spec.total_count:,} en {res_spec.execution_time_ms} ms")
    for r in res_spec.results[:3]:
        print(f"  - {r['nom']} ({r['categorie_recherche']}) - {r['commune']}, {r['wilaya']}")

    # 3. Test Proximité GPS (Alger Centre: 36.7538, 3.0588, r=5km)
    res_geo = engine.search(latitude=36.7538, longitude=3.0588, radius_km=5.0, limit=5)
    print(f"\n[Proximité Alger 5km] Trouvés: {res_geo.total_count:,} en {res_geo.execution_time_ms} ms")
    for r in res_geo.results[:3]:
        print(f"  - {r['nom']} à {r['distance_km']} km ({r['commune']}, {r['wilaya']})")
