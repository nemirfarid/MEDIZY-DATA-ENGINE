#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SANTÉ DZ / MEDIZY — MONITEUR DE SANTÉ ET D'AUTORÉPARATION (Phase 7)
==================================================================
Surveillance proactive et cyclique des services de l'API REST Santé DZ Medizy :
- Contrôle de santé système (/api/v1/health).
- Contrôle des métriques consolidées (/api/v1/stats).
- Vérification de l'intégrité du cache national mobile (/api/v1/cache/national).
- Surveillance des temps de réponse (seuil max : 200 ms).
- Autoréparation (redémarrage du service si défaillance critique ou latence anormale).
- Génération d'un rapport JSON d'audit de disponibilité.
"""

import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_LATENCY_THRESHOLD_MS = 200.0
DEFAULT_REPORT_PATH = (
    r"D:\SANTE_DZ_EXPORTS\logs\health_report.json"
    if os.path.exists(r"D:\SANTE_DZ_EXPORTS")
    else os.path.join(os.path.dirname(os.path.dirname(__file__)), "health_report.json")
)


class HealthCheckResult:
    """Résultat d'une vérification d'un endpoint."""

    def __init__(
        self,
        endpoint: str,
        status: str,  # 'OK', 'WARNING', 'CRITICAL'
        latency_ms: float,
        status_code: Optional[int] = None,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.endpoint = endpoint
        self.status = status
        self.latency_ms = round(latency_ms, 2)
        self.status_code = status_code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "status_code": self.status_code,
            "message": self.message,
            "details": self.details,
        }


class MedizyHealthMonitor:
    """Moniteur de santé autonome pour l'API REST Santé DZ Medizy."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        max_latency_ms: float = DEFAULT_LATENCY_THRESHOLD_MS,
        report_file: str = DEFAULT_REPORT_PATH,
        auto_restart: bool = False,
        restart_cmd: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.max_latency_ms = max_latency_ms
        self.report_file = report_file
        self.auto_restart = auto_restart
        self.restart_cmd = restart_cmd

    def _http_get(
        self, endpoint: str, timeout: float = 5.0, read_body: bool = True
    ) -> tuple[int, bytes, float]:
        """Exécute un GET HTTP et retourne (status_code, body, latency_ms)."""
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MedizyHealthMonitor/1.0",
                "Accept-Encoding": "identity",
            },
        )
        start_time = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.getcode()
            body = resp.read() if read_body else b""
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return status_code, body, elapsed_ms

    def check_health(self) -> HealthCheckResult:
        """Vérifie l'état de l'endpoint /api/v1/health."""
        endpoint = "/api/v1/health"
        try:
            status_code, body, latency_ms = self._http_get(endpoint)
            if status_code != 200:
                return HealthCheckResult(
                    endpoint=endpoint,
                    status="CRITICAL",
                    latency_ms=latency_ms,
                    status_code=status_code,
                    message=f"HTTP non conforme : {status_code}",
                )

            data = json.loads(body.decode("utf-8"))
            status_field = data.get("status")
            integrity = data.get("database", {}).get("sqlite_integrity")
            total_entries = data.get("database", {}).get("total_entries", 0)

            if status_field != "healthy" or integrity != "ok":
                return HealthCheckResult(
                    endpoint=endpoint,
                    status="CRITICAL",
                    latency_ms=latency_ms,
                    status_code=status_code,
                    message="Anomalie d'intégrité de la base ou statut non sain",
                    details=data,
                )

            status = "WARNING" if latency_ms > self.max_latency_ms else "OK"
            msg = (
                f"Latence élevée ({latency_ms:.1f} ms > {self.max_latency_ms} ms)"
                if status == "WARNING"
                else "Santé opérationnelle conforme"
            )

            return HealthCheckResult(
                endpoint=endpoint,
                status=status,
                latency_ms=latency_ms,
                status_code=status_code,
                message=msg,
                details={
                    "total_entries": total_entries,
                    "sqlite_integrity": integrity,
                    "sha256": data.get("database", {}).get("sha256"),
                },
            )

        except urllib.error.URLError as e:
            return HealthCheckResult(
                endpoint=endpoint,
                status="CRITICAL",
                latency_ms=0.0,
                message=f"Échec de connexion : {e.reason}",
            )
        except Exception as e:
            return HealthCheckResult(
                endpoint=endpoint,
                status="CRITICAL",
                latency_ms=0.0,
                message=f"Erreur inattendue : {str(e)}",
            )

    def check_stats(self) -> HealthCheckResult:
        """Vérifie l'état de l'endpoint /api/v1/stats."""
        endpoint = "/api/v1/stats"
        try:
            status_code, body, latency_ms = self._http_get(endpoint)
            if status_code != 200:
                return HealthCheckResult(
                    endpoint=endpoint,
                    status="CRITICAL",
                    latency_ms=latency_ms,
                    status_code=status_code,
                    message=f"HTTP non conforme : {status_code}",
                )

            data = json.loads(body.decode("utf-8"))
            metrics = data.get("metrics", {})
            total = metrics.get("total_facilities", 0)
            wilayas = metrics.get("wilayas_covered", 0)

            if total < 30000 or wilayas < 58:
                return HealthCheckResult(
                    endpoint=endpoint,
                    status="CRITICAL",
                    latency_ms=latency_ms,
                    status_code=status_code,
                    message=f"Données incomplètes (établissements: {total}, wilayas: {wilayas})",
                    details=metrics,
                )

            status = "WARNING" if latency_ms > self.max_latency_ms else "OK"
            msg = (
                f"Latence élevée ({latency_ms:.1f} ms > {self.max_latency_ms} ms)"
                if status == "WARNING"
                else "Métriques statistiques conformes"
            )

            return HealthCheckResult(
                endpoint=endpoint,
                status=status,
                latency_ms=latency_ms,
                status_code=status_code,
                message=msg,
                details=metrics,
            )

        except urllib.error.URLError as e:
            return HealthCheckResult(
                endpoint=endpoint,
                status="CRITICAL",
                latency_ms=0.0,
                message=f"Échec de connexion : {e.reason}",
            )
        except Exception as e:
            return HealthCheckResult(
                endpoint=endpoint,
                status="CRITICAL",
                latency_ms=0.0,
                message=f"Erreur inattendue : {str(e)}",
            )

    def check_cache(self) -> HealthCheckResult:
        """Vérifie la disponibilité du cache mobile /api/v1/cache/national."""
        endpoint = "/api/v1/cache/national"
        try:
            # Ne charge que les métadonnées et le stream
            url = f"{self.base_url}{endpoint}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MedizyHealthMonitor/1.0"},
            )
            start_time = time.perf_counter()
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                status_code = resp.getcode()
                content_type = resp.headers.get("Content-Type", "")
                sample = resp.read()
                latency_ms = (time.perf_counter() - start_time) * 1000.0

            if status_code != 200:
                return HealthCheckResult(
                    endpoint=endpoint,
                    status="CRITICAL",
                    latency_ms=latency_ms,
                    status_code=status_code,
                    message=f"HTTP non conforme : {status_code}",
                )

            # Vérification magic bytes GZIP (0x1f, 0x8b)
            if len(sample) < 2 or sample[:2] != b"\x1f\x8b":
                return HealthCheckResult(
                    endpoint=endpoint,
                    status="CRITICAL",
                    latency_ms=latency_ms,
                    status_code=status_code,
                    message="Le fichier retourné n'est pas une archive GZIP valide",
                )

            status = "WARNING" if latency_ms > self.max_latency_ms else "OK"
            msg = (
                f"Latence élevée ({latency_ms:.1f} ms > {self.max_latency_ms} ms)"
                if status == "WARNING"
                else "Flux de cache mobile opérationnel"
            )

            return HealthCheckResult(
                endpoint=endpoint,
                status=status,
                latency_ms=latency_ms,
                status_code=status_code,
                message=msg,
                details={"content_type": content_type, "sample_bytes": len(sample)},
            )

        except urllib.error.URLError as e:
            return HealthCheckResult(
                endpoint=endpoint,
                status="CRITICAL",
                latency_ms=0.0,
                message=f"Échec de connexion : {e.reason}",
            )
        except Exception as e:
            return HealthCheckResult(
                endpoint=endpoint,
                status="CRITICAL",
                latency_ms=0.0,
                message=f"Erreur inattendue : {str(e)}",
            )

    def trigger_autorestart(self) -> Dict[str, Any]:
        """Déclenche la procédure de redémarrage d'urgence du service."""
        result = {"triggered": True, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        
        if self.restart_cmd:
            cmd = self.restart_cmd
        elif platform.system() == "Windows":
            script = os.path.abspath(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment", "start_windows_service.ps1")
            )
            cmd = f'powershell.exe -ExecutionPolicy Bypass -File "{script}" -Action restart'
        else:
            cmd = "systemctl restart medizy"

        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            result["exit_code"] = res.returncode
            result["stdout"] = res.stdout.strip()
            result["stderr"] = res.stderr.strip()
            result["success"] = (res.returncode == 0)
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def run_cycle(self) -> Dict[str, Any]:
        """Exécute un cycle complet de vérification et retourne le rapport."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        health_res = self.check_health()
        stats_res = self.check_stats()
        cache_res = self.check_cache()

        results = [health_res, stats_res, cache_res]
        
        critical_count = sum(1 for r in results if r.status == "CRITICAL")
        warning_count = sum(1 for r in results if r.status == "WARNING")
        
        if critical_count > 0:
            overall_status = "DOWN"
        elif warning_count > 0:
            overall_status = "DEGRADED"
        else:
            overall_status = "HEALTHY"

        avg_latency = sum(r.latency_ms for r in results) / len(results)

        report = {
            "timestamp": timestamp,
            "overall_status": overall_status,
            "base_url": self.base_url,
            "threshold_latency_ms": self.max_latency_ms,
            "average_latency_ms": round(avg_latency, 2),
            "critical_incidents": critical_count,
            "warning_incidents": warning_count,
            "checks": {
                "health": health_res.to_dict(),
                "stats": stats_res.to_dict(),
                "cache_national": cache_res.to_dict(),
            },
        }

        # Déclenchement d'autoréparation si service DOWN et auto_restart activé
        if overall_status == "DOWN" and self.auto_restart:
            print(f"[{timestamp}] ALERTE : Service DOWN détecté. Déclenchement de l'autoréparation...")
            restart_info = self.trigger_autorestart()
            report["auto_repair"] = restart_info
        elif overall_status == "DEGRADED":
            print(f"[{timestamp}] AVERTISSEMENT : Service DÉGRADÉ (latence moyenne : {avg_latency:.1f} ms)")

        self.save_report(report)
        return report

    def save_report(self, report: Dict[str, Any]):
        """Écrit le rapport formaté en JSON sur le support de stockage configuré."""
        try:
            log_dir = os.path.dirname(self.report_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            with open(self.report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERREUR] Impossible d'écrire le rapport sur {self.report_file}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Moniteur de santé Santé DZ Medizy")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="URL de base de l'API REST")
    parser.add_argument("--interval", type=int, default=10, help="Intervalle entre les vérifications en secondes")
    parser.add_argument("--once", action="store_true", help="Exécute un seul cycle puis s'arrête")
    parser.add_argument("--max-latency-ms", type=float, default=DEFAULT_LATENCY_THRESHOLD_MS, help="Seuil de latence critique (ms)")
    parser.add_argument("--report-file", default=DEFAULT_REPORT_PATH, help="Fichier de sortie du rapport JSON")
    parser.add_argument("--auto-restart", action="store_true", help="Déclenche le redémarrage automatique en cas de panne")
    parser.add_argument("--restart-cmd", default=None, help="Commande personnalisée de redémarrage")

    args = parser.parse_args()

    monitor = MedizyHealthMonitor(
        base_url=args.url,
        max_latency_ms=args.max_latency_ms,
        report_file=args.report_file,
        auto_restart=args.auto_restart,
        restart_cmd=args.restart_cmd,
    )

    print("=" * 70)
    print("SANTÉ DZ / MEDIZY — MONITEUR DE SANTÉ EN SERVICE")
    print(f"  * Cible API      : {monitor.base_url}")
    print(f"  * Seuil Latence  : {monitor.max_latency_ms} ms")
    print(f"  * Rapport JSON   : {monitor.report_file}")
    print(f"  * Auto-Repair    : {'Activé' if monitor.auto_restart else 'Désactivé'}")
    print("=" * 70)

    if args.once:
        rep = monitor.run_cycle()
        print(f"Statut global : {rep['overall_status']} (Latence moy: {rep['average_latency_ms']} ms)")
        sys.exit(0 if rep["overall_status"] == "HEALTHY" else (1 if rep["overall_status"] == "DOWN" else 2))

    try:
        while True:
            rep = monitor.run_cycle()
            print(f"[{rep['timestamp']}] Statut: {rep['overall_status']} | Latence: {rep['average_latency_ms']} ms")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nArrêt du moniteur de santé.")


if __name__ == "__main__":
    main()
