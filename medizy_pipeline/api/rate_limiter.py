#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Middleware & Dépendance de Limitation de Débit (Rate Limiting)
==================================================================================
Protection contre les attaques par déni de service (DoS) et de force brute sur les
points d'entrée d'authentification et de modération administrative.
Supporte Redis en production avec fallback transparent en mémoire vive.
"""

import logging
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, Response, status

logger = logging.getLogger("medizy.rate_limiter")

# Configuration Redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class InMemoryBackend:
    """Stockage mémoire local avec algorithme de fenêtre glissante (Sliding Window)."""

    def __init__(self):
        self._records: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, key: str, times: int, seconds: int) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - seconds

        # Nettoyage des timestamps expirés
        timestamps = [ts for ts in self._records[key] if ts > window_start]
        self._records[key] = timestamps

        current_count = len(timestamps)
        if current_count >= times:
            oldest = timestamps[0] if timestamps else now
            retry_after = max(1, int(oldest + seconds - now))
            return True, current_count, retry_after

        # Enregistrement de la requête actuelle
        self._records[key].append(now)
        remaining = max(0, times - (current_count + 1))
        return False, remaining, seconds


class RedisBackend:
    """Stockage distribué Redis pour environnements de production multi-instances."""

    def __init__(self, redis_url: str):
        import redis
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        # Test de connexion
        self.client.ping()

    def is_rate_limited(self, key: str, times: int, seconds: int) -> tuple[bool, int, int]:
        pipe = self.client.pipeline()
        now = time.time()
        window_start = now - seconds

        # Algorithme de fenêtre glissante via ZSET
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, seconds + 5)
        results = pipe.execute()

        current_count = results[1]
        if current_count >= times:
            return True, current_count, seconds

        remaining = max(0, times - (current_count + 1))
        return False, remaining, seconds


# Sélection du moteur de rate limiting
_storage_backend = None
try:
    if os.environ.get("USE_REDIS", "false").lower() in ("true", "1", "yes"):
        _storage_backend = RedisBackend(REDIS_URL)
        logger.info(f"Moteur de Rate Limiting initialisé sur Redis: {REDIS_URL}")
except Exception as e:
    logger.warning(f"Connexion Redis non disponible ({e}). Utilisation du backend mémoire.")

if _storage_backend is None:
    _storage_backend = InMemoryBackend()
    logger.info("Moteur de Rate Limiting initialisé en mémoire locale (Sliding Window).")


def get_client_ip(request: Request) -> str:
    """Extrait l'adresse IP réelle du client en tenant compte des reverse-proxies (Nginx, Traefik)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


class RateLimiter:
    """Dépendance FastAPI appliquant un quota de requêtes par fenêtre temporelle."""

    def __init__(self, times: int = 60, seconds: int = 60, prefix: str = "general"):
        self.times = times
        self.seconds = seconds
        self.prefix = prefix

    def __call__(self, request: Request, response: Response):
        ip = get_client_ip(request)
        rate_key = f"rate:{self.prefix}:{ip}"

        is_limited, remaining, retry_after = _storage_backend.is_rate_limited(
            key=rate_key,
            times=self.times,
            seconds=self.seconds,
        )

        # En-têtes standards RFC de Rate Limiting
        response.headers["X-RateLimit-Limit"] = str(self.times)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + retry_after))

        if is_limited:
            logger.warning(f"Blocage Rate-Limit pour l'IP {ip} sur {request.url.path} (Quota {self.times}/{self.seconds}s dépassé).")
            response.headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Trop de requêtes. Veuillez patienter {retry_after} secondes avant de réessayer.",
                headers={"Retry-After": str(retry_after)},
            )
        return True


# Quotas prédéfinis prêts à l'emploi
# 5 tentatives par minute sur les endpoints de login (anti-brute force)
login_rate_limiter = RateLimiter(times=5, seconds=60, prefix="auth_login")

# 60 actions par minute sur le back-office modération
admin_action_rate_limiter = RateLimiter(times=60, seconds=60, prefix="admin_moderation")
