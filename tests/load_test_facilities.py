#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Banc de Test de Charge & Tenue en Concurrence
================================================================
Simule un trafic national intensif sur l'API cartographique MEDIZY :
  - 70% Requêtes spatiales radiales (/api/v1/facilities/nearby) autour de 5 métropoles
  - 20% Recherches textuelles plein-texte (/api/v1/facilities/search) avec filtres
  - 8%  Extractions incrémentales NIBRAS (/api/v1/facilities/export/latest)
  - 2%  Soumissions citoyennes (/api/v1/facilities/suggest)

Mesure les latences p50, p95, p99, le débit (RPS) et vérifie le taux d'erreur (< 0.1%).
"""

import argparse
import asyncio
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:
    print("ERREUR : httpx est requis. Installez-le via 'pip install httpx'.", file=sys.stderr)
    sys.exit(1)


# Métropoles nationales de référence (lat, lon, nom)
METROPOLES = [
    {"name": "Alger", "lat": 36.7538, "lon": 3.0588},
    {"name": "Oran", "lat": 35.6987, "lon": -0.6349},
    {"name": "Constantine", "lat": 36.3650, "lon": 6.6147},
    {"name": "Annaba", "lat": 36.9000, "lon": 7.7667},
    {"name": "Mostaganem", "lat": 35.9312, "lon": 0.0892},
]

SEARCH_KEYWORDS = [
    "CHU", "EPH", "EPSP", "Polyclinique", "Clinique", "Hôpital",
    "Cardiologie", "Pédiatrie", "Maternité", "Urgences", "Radiologie",
    "Ophtalmologie", "Ibn Ziri", "Mustapha", "Nefissa", "Frantz Fanon",
    "Cabinet", "Centre de Santé", "Médecine Générale", "Scanner"
]

FACILITY_TYPES = [
    "CHU", "EPH", "EPSP", "Clinique", "Polyclinique", "Urgences", "Cabinet Médical"
]

WILAYAS = [
    "Alger", "Oran", "Constantine", "Annaba", "Mostaganem",
    "Blida", "Tlemcen", "Sétif", "Batna", "Béjaïa"
]


@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    duration_ms: float
    success: bool
    error_msg: Optional[str] = None


@dataclass
class ScenarioStats:
    total_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    durations: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=dict)

    def add(self, res: RequestResult):
        self.total_requests += 1
        if res.success:
            self.success_requests += 1
        else:
            self.failed_requests += 1
        self.durations.append(res.duration_ms)
        self.status_codes[res.status_code] = self.status_codes.get(res.status_code, 0) + 1

    def percentile(self, p: float) -> float:
        if not self.durations:
            return 0.0
        sorted_d = sorted(self.durations)
        k = (len(sorted_d) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_d[int(k)]
        d0 = sorted_d[int(f)] * (c - k)
        d1 = sorted_d[int(c)] * (k - f)
        return d0 + d1


class LoadTestEngine:
    def __init__(self, base_url: str, concurrency: int, total_requests: int, timeout_sec: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.concurrency = concurrency
        self.total_requests = total_requests
        self.timeout_sec = timeout_sec
        self.semaphore = asyncio.Semaphore(concurrency)
        self.overall_stats = ScenarioStats()
        self.category_stats: Dict[str, ScenarioStats] = {
            "nearby_70%": ScenarioStats(),
            "search_20%": ScenarioStats(),
            "export_8%": ScenarioStats(),
            "suggest_2%": ScenarioStats(),
        }

    def _generate_nearby_params(self) -> Tuple[str, Dict[str, Any]]:
        metro = random.choice(METROPOLES)
        # Jitter de ~5 km autour de la métropole
        lat = metro["lat"] + random.uniform(-0.045, 0.045)
        lon = metro["lon"] + random.uniform(-0.045, 0.045)
        radius = random.choice([2.0, 5.0, 8.0, 10.0, 15.0])
        params = {
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "radius_km": radius,
            "limit": random.choice([10, 20, 50]),
        }
        if random.random() < 0.4:
            params["type"] = random.choice(FACILITY_TYPES)
        return "/api/v1/facilities/nearby", params

    def _generate_search_params(self) -> Tuple[str, Dict[str, Any]]:
        params = {
            "limit": random.choice([10, 20, 50]),
            "offset": random.choice([0, 10]),
        }
        roll = random.random()
        if roll < 0.5:
            params["q"] = random.choice(SEARCH_KEYWORDS)
        if roll >= 0.3:
            params["wilaya"] = random.choice(WILAYAS)
        if random.random() < 0.4:
            params["type"] = random.choice(FACILITY_TYPES)
        return "/api/v1/facilities/search", params

    def _generate_export_params(self) -> Tuple[str, Dict[str, Any]]:
        params = {
            "limit": random.choice([20, 50, 100]),
        }
        if random.random() < 0.5:
            params["cursor"] = str(random.randint(1, 1000))
        if random.random() < 0.3:
            params["wilaya"] = random.choice(WILAYAS)
        return "/api/v1/facilities/export/latest", params

    def _generate_suggest_payload(self) -> Tuple[str, Dict[str, Any]]:
        metro = random.choice(METROPOLES)
        lat = metro["lat"] + random.uniform(-0.02, 0.02)
        lon = metro["lon"] + random.uniform(-0.02, 0.02)
        idx = random.randint(1000, 9999)
        payload = {
            "name": f"Cabinet Médical Test Charge #{idx}",
            "type": "Cabinet Médical",
            "wilaya": metro["name"],
            "commune": f"Commune {metro['name']}",
            "address": f"Rue des Martyrs #{idx}",
            "phone": f"021 {random.randint(10, 99)} {random.randint(10, 99)} {random.randint(10, 99)}",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "google_maps_url": f"https://maps.google.com/?q={lat:.5f},{lon:.5f}",
            "submitter_name": "Robot Benchmarking MEDIZY",
            "submitter_email": "bench@medizy.dz",
            "submitter_notes": "Test de résistance et d'écriture concurrente sous charge.",
        }
        return "/api/v1/facilities/suggest", payload

    async def _execute_single_request(self, client: httpx.AsyncClient, req_index: int) -> RequestResult:
        # Distribution : 70% nearby, 20% search, 8% export, 2% suggest
        roll = random.random()
        if roll < 0.70:
            category = "nearby_70%"
            path, params = self._generate_nearby_params()
            method = "GET"
            payload = None
        elif roll < 0.90:
            category = "search_20%"
            path, params = self._generate_search_params()
            method = "GET"
            payload = None
        elif roll < 0.98:
            category = "export_8%"
            path, params = self._generate_export_params()
            method = "GET"
            payload = None
        else:
            category = "suggest_2%"
            path, payload = self._generate_suggest_payload()
            method = "POST"
            params = None

        url = f"{self.base_url}{path}"
        t0 = time.perf_counter()

        async with self.semaphore:
            try:
                if method == "GET":
                    resp = await client.get(url, params=params)
                else:
                    resp = await client.post(url, json=payload)
                duration_ms = (time.perf_counter() - t0) * 1000.0
                success = 200 <= resp.status_code < 300
                res = RequestResult(
                    endpoint=category,
                    status_code=resp.status_code,
                    duration_ms=duration_ms,
                    success=success,
                    error_msg=None if success else f"HTTP {resp.status_code}: {resp.text[:120]}",
                )
            except Exception as e:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                res = RequestResult(
                    endpoint=category,
                    status_code=599,
                    duration_ms=duration_ms,
                    success=False,
                    error_msg=str(e),
                )

        self.overall_stats.add(res)
        self.category_stats[category].add(res)
        return res

    async def run(self) -> Dict[str, Any]:
        print("==============================================================================")
        print("    MEDIZY — Banc de Test de Charge & Haute Concurrence Nationale")
        print("==============================================================================")
        print(f"Cible API           : {self.base_url}")
        print(f"Nombre de requêtes  : {self.total_requests}")
        print(f"Concurrence max     : {self.concurrency} workers asynchrones")
        print(f"Distribution ciblée : 70% nearby | 20% search | 8% export | 2% suggest")
        print("==============================================================================")

        limits = httpx.Limits(
            max_connections=self.concurrency + 20,
            max_keepalive_connections=self.concurrency,
        )
        timeout = httpx.Timeout(self.timeout_sec, connect=5.0)

        t_start = time.perf_counter()
        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            tasks = [
                self._execute_single_request(client, i)
                for i in range(self.total_requests)
            ]
            await asyncio.gather(*tasks)

        t_total = time.perf_counter() - t_start
        rps = self.total_requests / t_total if t_total > 0 else 0.0

        error_rate = (
            (self.overall_stats.failed_requests / self.total_requests) * 100.0
            if self.total_requests > 0
            else 0.0
        )

        p50 = self.overall_stats.percentile(50)
        p95 = self.overall_stats.percentile(95)
        p99 = self.overall_stats.percentile(99)
        avg_d = sum(self.overall_stats.durations) / len(self.overall_stats.durations) if self.overall_stats.durations else 0.0

        print("\n" + "=" * 78)
        print("                       RÉSULTATS DU BENCHMARK GLOBAL")
        print("=" * 78)
        print(f"Durée totale du test   : {t_total:.2f} s")
        print(f"Débit moyen (RPS)      : {rps:.1f} req/s")
        print(f"Total requêtes         : {self.overall_stats.total_requests}")
        print(f"Succès (2xx)           : {self.overall_stats.success_requests}")
        print(f"Échecs                 : {self.overall_stats.failed_requests}")
        print(f"Taux d'erreur          : {error_rate:.3f}% (SLA exigé < 0.100%)")
        print("-" * 78)
        print(f"Latence Moyenne        : {avg_d:.2f} ms")
        print(f"Latence Médiane (p50)  : {p50:.2f} ms")
        print(f"Latence 95e pct (p95)  : {p95:.2f} ms (SLA garanti < 50.00 ms)")
        print(f"Latence 99e pct (p99)  : {p99:.2f} ms (SLA garanti < 100.00 ms)")
        print(f"Codes de statut        : {dict(self.overall_stats.status_codes)}")
        print("=" * 78)

        print("\n" + "-" * 78)
        print(f"{'Scénario / Endpoint':<20} | {'Reqs':<6} | {'Part':<6} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'p99 (ms)':<9} | {'Erreurs'}")
        print("-" * 78)
        for cat_name, s in self.category_stats.items():
            pct_share = (s.total_requests / self.total_requests * 100.0) if self.total_requests > 0 else 0
            c_p50 = s.percentile(50)
            c_p95 = s.percentile(95)
            c_p99 = s.percentile(99)
            print(f"{cat_name:<20} | {s.total_requests:<6} | {pct_share:>5.1f}% | {c_p50:>8.2f} | {c_p95:>8.2f} | {c_p99:>8.2f} | {s.failed_requests}")
        print("-" * 78)

        sla_passed = (error_rate <= 0.1) and (p95 <= 50.0) and (p99 <= 100.0)
        status_msg = "CONFORME AUX SLA DE PRODUCTION" if sla_passed else "NON-CONFORME AUX SLA"
        print(f"\nStatut de Validation : [{'PASS' if sla_passed else 'FAIL'}] {status_msg}")
        print("=" * 78 + "\n")

        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_url": self.base_url,
            "total_requests": self.total_requests,
            "concurrency": self.concurrency,
            "duration_seconds": round(t_total, 2),
            "requests_per_second": round(rps, 2),
            "error_rate_pct": round(error_rate, 4),
            "latencies_ms": {
                "avg": round(avg_d, 2),
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            },
            "sla_passed": sla_passed,
            "status_codes": self.overall_stats.status_codes,
            "breakdown": {
                k: {
                    "count": v.total_requests,
                    "failed": v.failed_requests,
                    "p50": round(v.percentile(50), 2),
                    "p95": round(v.percentile(95), 2),
                    "p99": round(v.percentile(99), 2),
                }
                for k, v in self.category_stats.items()
            },
        }
        return summary


def main():
    parser = argparse.ArgumentParser(description="Banc de test de charge MEDIZY PostGIS")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="URL de base de l'API")
    parser.add_argument("--concurrency", "-c", type=int, default=50, help="Nombre de workers concurrents")
    parser.add_argument("--requests", "-n", type=int, default=500, help="Nombre total de requêtes à simuler")
    parser.add_argument("--timeout", type=float, default=15.0, help="Délai d'expiration HTTP en secondes")
    parser.add_argument("--output-json", default=None, help="Chemin du fichier JSON de sortie")
    args = parser.parse_args()

    engine = LoadTestEngine(
        base_url=args.base_url,
        concurrency=args.concurrency,
        total_requests=args.requests,
        timeout_sec=args.timeout,
    )
    results = asyncio.run(engine.run())

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Rapport JSON consigné dans : {args.output_json}")

    sys.exit(0 if results["sla_passed"] else 1)


if __name__ == "__main__":
    main()
