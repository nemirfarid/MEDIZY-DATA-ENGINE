#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Client de Référence Cache Mobile Offline-First (Phase 10)
=============================================================================
Simule le comportement d'un terminal mobile (Flutter / React Native / Kotlin / Swift) :
1. Interroge /api/v1/cache/version pour détecter d'éventuelles modifications (delta).
2. Télécharge de manière conditionnelle l'archive compressée (GZIP).
3. Décompresse l'archive en mémoire et met à jour le stockage local (.mobile_cache/).
4. Exécute des recherches multicritères et géospatiales en local sans réseau (100% offline).

Usage :
-------
    python client_cache_consumer.py --demo-search "cardiologue Alger"
    python client_cache_consumer.py --nearby 36.7538 3.0588 5.0
    python client_cache_consumer.py --force-download
"""

import argparse
import datetime
import gzip
import json
import math
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

LOCAL_CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".mobile_cache"))
LOCAL_DATA_FILE = os.path.join(LOCAL_CACHE_DIR, "medizy_local_data.json")
LOCAL_META_FILE = os.path.join(LOCAL_CACHE_DIR, "medizy_cache_metadata.json")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcul géodésique Haversine en kilomètres."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999999.0
    r = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def ensure_server_running(host: str = "127.0.0.1", port: int = 8000):
    """
    Vérifie si le serveur API est déjà actif sur host:port.
    Si non actif, lance un serveur embarqué en tâche de fond (daemon thread).
    """
    test_url = f"http://{host}:{port}/health"
    try:
        req = urllib.request.Request(test_url, headers={"User-Agent": "MedizyProbe/1.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                return  # Serveur externe déjà actif
    except Exception:
        pass

    # Lancement d'un serveur embarqué
    from http.server import ThreadingHTTPServer
    from api_server import MedizyAPIHandler, calculate_sha256, DB_PATH
    from medizy_search import MedizySearchEngine

    engine = MedizySearchEngine(db_path=DB_PATH)
    MedizyAPIHandler.engine = engine
    MedizyAPIHandler.db_sha256 = calculate_sha256(DB_PATH)

    server = ThreadingHTTPServer((host, port), MedizyAPIHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)


class LocalOfflineSearchEngine:
    """Moteur de recherche 100% autonome exécuté sur le cache local en mémoire."""

    def __init__(self, facilities: List[Dict[str, Any]], metadata: Dict[str, Any]):
        self.facilities = facilities
        self.metadata = metadata

    def search(
        self,
        query: Optional[str] = None,
        wilaya: Optional[str] = None,
        commune: Optional[str] = None,
        specialite: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Recherche plein texte, facettes et distance géodésique sur la mémoire vive."""
        t0 = time.perf_counter()
        matches = []

        query_tokens = [tok.lower().strip() for tok in (query or "").split()] if query else []
        wilaya_clean = wilaya.lower().strip() if wilaya else None
        commune_clean = commune.lower().strip() if commune else None
        spec_clean = specialite.lower().strip() if specialite else None

        geo_mode = (latitude is not None and longitude is not None and radius_km is not None)

        for fac in self.facilities:
            f_nom = (fac.get("nom") or "").lower()
            f_wil = (fac.get("wil") or "").lower()
            f_com = (fac.get("com") or "").lower()
            f_cat = (fac.get("cat") or "").lower()
            f_adr = (fac.get("adr") or "").lower()

            # Filtre Wilaya
            if wilaya_clean and wilaya_clean not in f_wil:
                continue

            # Filtre Commune
            if commune_clean and commune_clean not in f_com:
                continue

            # Filtre Spécialité
            if spec_clean and spec_clean not in f_cat:
                continue

            # Filtre Texte libre multi-tokens
            if query_tokens:
                combined_text = f"{f_nom} {f_cat} {f_wil} {f_com} {f_adr}"
                if not all(tok in combined_text for tok in query_tokens):
                    continue

            # Filtre et calcul géospatial
            dist = None
            if geo_mode:
                f_lat = fac.get("lat")
                f_lon = fac.get("lon")
                if f_lat is None or f_lon is None:
                    continue
                dist = haversine_distance(latitude, longitude, f_lat, f_lon)
                if dist > radius_km:
                    continue

            item = dict(fac)
            if dist is not None:
                item["distance_km"] = round(dist, 3)
            matches.append(item)

        # Tri : par distance si mode géo, sinon par nom
        if geo_mode:
            matches.sort(key=lambda x: x.get("distance_km", 999999.0))
        else:
            matches.sort(key=lambda x: x.get("nom", ""))

        t1 = time.perf_counter()
        elapsed_ms = round((t1 - t0) * 1000.0, 2)

        return {
            "total_found": len(matches),
            "execution_time_ms": elapsed_ms,
            "results": matches[:limit]
        }


class MobileCacheConsumer:
    """Client mobile offline-first gérant le cycle de synchronisation et la recherche."""

    def __init__(self, server_url: str = "http://127.0.0.1:8000", cache_dir: str = LOCAL_CACHE_DIR):
        self.server_url = server_url.rstrip("/")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.local_meta: Optional[Dict[str, Any]] = self._load_local_meta()
        self.search_engine: Optional[LocalOfflineSearchEngine] = None

    def _load_local_meta(self) -> Optional[Dict[str, Any]]:
        if os.path.exists(LOCAL_META_FILE):
            try:
                with open(LOCAL_META_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _save_local_meta(self, meta: Dict[str, Any]):
        with open(LOCAL_META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    def fetch_server_version(self) -> Dict[str, Any]:
        """Étape 1 : Interroge /api/v1/cache/version sur le serveur."""
        url = f"{self.server_url}/api/v1/cache/version"
        req = urllib.request.Request(url, headers={"User-Agent": "MedizyMobile/1.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)

    def sync_cache(self, force: bool = False, wilaya: Optional[str] = None) -> bool:
        """
        Cycle de synchronisation delta :
        1. Vérifie si le cache local correspond au SHA-256 du serveur.
        2. Télécharge l'archive GZIP uniquement en cas de divergence (ou force=True).
        3. Décompresse en mémoire et stocke le snapshot local.
        """
        print("-" * 70)
        print("CYCLE DE SYNCHRONISATION DU CACHE CLIENT MOBILE")
        print("-" * 70)
        print(f"Serveur distant  : {self.server_url}")
        print(f"Répertoire local : {self.cache_dir}")

        print("1. Interrogation de /api/v1/cache/version...")
        try:
            remote_info = self.fetch_server_version()
        except Exception as e:
            print(f"[ERREUR RÉSEAU] Impossible de contacter le serveur : {e}")
            if self.is_cache_ready():
                print("[FALLBACK OFFLINE] Utilisation du cache local existant.")
                return True
            raise

        remote_sha = remote_info.get("database_sha256")
        remote_count = remote_info.get("total_facilities")
        remote_version = remote_info.get("version")

        print(f"   * Version serveur   : {remote_version}")
        print(f"   * Empreinte SHA-256 : {remote_sha}")
        print(f"   * Établissements    : {remote_count:,}")

        local_sha = self.local_meta.get("database_sha256") if self.local_meta else None

        # Vérification de synchronisation
        if not force and self.local_meta and local_sha == remote_sha and os.path.exists(LOCAL_DATA_FILE):
            print(f"\n[SYNC OK] Cache local à jour (SHA-256: {local_sha[:16]}...).")
            print("Aucun transfert réseau requis. Utilisation du cache hors-ligne.")
            return False

        # Téléchargement conditionnel
        if wilaya:
            download_url = f"{self.server_url}/api/v1/cache/wilaya/{wilaya}"
            archive_name = f"cache_wilaya_{wilaya}.json.gz"
        else:
            download_url = f"{self.server_url}/api/v1/cache/national"
            archive_name = "medizy_national_cache.json.gz"

        print(f"\n2. Mise à jour requise -> Téléchargement de {download_url}...")
        t0 = time.perf_counter()
        req = urllib.request.Request(download_url, headers={"User-Agent": "MedizyMobile/1.0"})
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            gz_bytes = resp.read()
        t1 = time.perf_counter()
        dl_ms = (t1 - t0) * 1000.0

        compressed_kb = len(gz_bytes) / 1024.0
        print(f"   * Archive reçue : {compressed_kb:.1f} Ko GZIP en {dl_ms:.1f} ms")

        # 3. Décompression en mémoire
        print("3. Décompression GZIP en mémoire vive...")
        t_dec0 = time.perf_counter()
        json_str = gzip.decompress(gz_bytes).decode("utf-8")
        parsed = json.loads(json_str)
        t_dec1 = time.perf_counter()
        dec_ms = (t_dec1 - t_dec0) * 1000.0

        facilities = parsed.get("facilities", [])
        raw_mb = len(json_str.encode("utf-8")) / (1024.0 * 1024.0)
        print(f"   * Décompressé : {raw_mb:.2f} Mo JSON ({len(facilities):,} établissements) en {dec_ms:.1f} ms")

        # 4. Écriture du cache local
        with open(LOCAL_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False)

        new_meta = {
            "version": remote_version,
            "database_sha256": remote_sha,
            "total_facilities": len(facilities),
            "synced_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_url": download_url,
            "compressed_size_kb": round(compressed_kb, 1),
            "raw_size_mb": round(raw_mb, 2)
        }
        self._save_local_meta(new_meta)
        self.local_meta = new_meta

        print(f"[SUCCÈS] Cache local stocké dans {LOCAL_DATA_FILE}")
        return True

    def is_cache_ready(self) -> bool:
        return os.path.exists(LOCAL_DATA_FILE) and os.path.exists(LOCAL_META_FILE)

    def load_search_engine(self) -> LocalOfflineSearchEngine:
        """Charge les données du cache local en mémoire vive pour la recherche instantanée."""
        if not self.is_cache_ready():
            raise RuntimeError("Le cache local n'est pas encore initialisé. Lancez sync_cache() d'abord.")

        if self.search_engine is None:
            t0 = time.perf_counter()
            with open(LOCAL_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            t1 = time.perf_counter()
            facilities = data.get("facilities", [])
            metadata = data.get("metadata", {})
            self.search_engine = LocalOfflineSearchEngine(facilities, metadata)
            print(f"[MÉMOIRE] {len(facilities):,} fiches chargées dans l'index mémoire en {(t1-t0)*1000.0:.1f} ms.")

        return self.search_engine


def main():
    parser = argparse.ArgumentParser(description="Client mobile offline-first Medizy Santé DZ")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="URL du serveur API")
    parser.add_argument("--wilaya", help="Code ou nom de wilaya pour sync partitionnée")
    parser.add_argument("--force-download", action="store_true", help="Forcer le re-téléchargement du cache")
    parser.add_argument("--demo-search", help="Requête de recherche locale de démonstration (ex: 'cardiologue Alger')")
    parser.add_argument("--nearby", nargs=3, metavar=("LAT", "LON", "RADIUS"), help="Recherche locale par proximité GPS")

    args = parser.parse_args()

    # Assure que le serveur est disponible
    ensure_server_running(port=8000)

    consumer = MobileCacheConsumer(server_url=args.server)

    # 1. Synchronisation conditionnelle
    consumer.sync_cache(force=args.force_download, wilaya=args.wilaya)

    # 2. Chargement du moteur local
    engine = consumer.load_search_engine()

    # 3. Démonstration de recherche locale offline
    query_str = args.demo_search or "cardiologue Alger"
    print("\n" + "=" * 70)
    print(f"RECHERCHE LOCALE HORS-LIGNE (OFFLINE) : '{query_str}'")
    print("=" * 70)

    res = engine.search(query=query_str, limit=5)
    print(f"Résultats trouvés : {res['total_found']:,} établissements")
    print(f"Temps d'exécution : {res['execution_time_ms']} ms (recherche 100% mémoire locale)")
    print("-" * 70)

    for i, fac in enumerate(res["results"], 1):
        nom = fac.get("nom", "Sans nom")
        cat = fac.get("cat", "Catégorie inconnue")
        wil = fac.get("wil", "")
        com = fac.get("com", "")
        tel = fac.get("tel") or "Non renseigné"
        adr = fac.get("adr") or "Adresse non précisée"
        lat = fac.get("lat")
        lon = fac.get("lon")
        print(f"#{i} {nom}")
        print(f"    Spécialité : {cat} | Commune: {com}, {wil}")
        print(f"    Téléphone  : {tel}")
        print(f"    Adresse    : {adr}")
        print(f"    GPS        : ({lat}, {lon})")
        print()

    # Si recherche par coordonnées demandée
    if args.nearby:
        lat = float(args.nearby[0])
        lon = float(args.nearby[1])
        radius = float(args.nearby[2])
        print("=" * 70)
        print(f"RECHERCHE PROXIMITÉ LOCALE (GPS: {lat}, {lon} | Rayon: {radius} km)")
        print("=" * 70)
        geo_res = engine.search(latitude=lat, longitude=lon, radius_km=radius, limit=5)
        print(f"Trouvés dans le rayon : {geo_res['total_found']} en {geo_res['execution_time_ms']} ms")
        for i, fac in enumerate(geo_res["results"], 1):
            print(f"#{i} {fac['nom']} à {fac.get('distance_km')} km ({fac.get('com')}, {fac.get('wil')})")


if __name__ == "__main__":
    main()
