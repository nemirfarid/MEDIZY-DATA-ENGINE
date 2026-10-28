#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Module de Sécurité & Authentification JWT
=============================================================
Fournit l'authentification par jeton JWT (RFC 7519) avec expiration,
le contrôle d'accès basé sur les rôles (RBAC) pour les administrateurs
et la compatibilité d'urgence avec clé d'API système.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import os
from typing import Any, Dict, Optional
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("medizy.security")

# Configuration de chiffrement des jetons et conformité production
ENV = os.environ.get("ENV", os.environ.get("ENVIRONMENT", "development")).lower()

_raw_jwt_secret = os.environ.get("ADMIN_JWT_SECRET") or os.environ.get("JWT_SECRET_KEY")
if not _raw_jwt_secret:
    if ENV in ("production", "prod"):
        raise RuntimeError("SÉCURITÉ CRITIQUE : ADMIN_JWT_SECRET obligatoire en environnement de production !")
    _raw_jwt_secret = "medizy-jwt-super-secret-key-production-change-me-2026"
    logger.warning("ATTENTION SÉCURITÉ : Clé JWT par défaut utilisée en mode local/test. Définir ADMIN_JWT_SECRET en production.")
JWT_SECRET_KEY = _raw_jwt_secret
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))

# Identifiants administrateur (surchargés via variables d'environnement)
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin@medizy.dz")

_raw_admin_password = os.environ.get("ADMIN_PASSWORD")
if not _raw_admin_password:
    if ENV in ("production", "prod"):
        raise RuntimeError("SÉCURITÉ CRITIQUE : ADMIN_PASSWORD obligatoire en environnement de production !")
    _raw_admin_password = "MedizyAdmin2026!"
ADMIN_PASSWORD = _raw_admin_password

_raw_admin_key = os.environ.get("ADMIN_API_KEY")
if not _raw_admin_key:
    if ENV in ("production", "prod"):
        raise RuntimeError("SÉCURITÉ CRITIQUE : ADMIN_API_KEY obligatoire en environnement de production !")
    _raw_admin_key = "medizy-admin-secret-key-2026"
SYSTEM_ADMIN_KEY = _raw_admin_key

security_bearer = HTTPBearer(auto_error=False)



def create_access_token(
    subject: str,
    name: str = "Admin MEDIZY",
    role: str = "superadmin",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Génère un jeton JWT signé avec date d'expiration."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)

    payload = {
        "sub": subject,
        "name": name,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "medizy-auth-service",
    }
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Décode et valide la signature et la durée de validité du jeton JWT."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Le jeton d'authentification a expiré. Veuillez vous reconnecter.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The token expired\""},
        )
    except jwt.PyJWTError as e:
        logger.warning(f"Tentative d'accès avec jeton JWT invalide: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton d'authentification invalide ou corrompu.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )


def verify_admin_credentials(username: str, password: str) -> bool:
    """Vérifie les identifiants administrateur avec comparaison en temps constant (anti-timing attacks)."""
    expected_user = os.environ.get("ADMIN_USERNAME", ADMIN_USERNAME)
    expected_pass = os.environ.get("ADMIN_PASSWORD", ADMIN_PASSWORD)

    user_match = hmac.compare_digest(username.strip(), expected_user.strip())
    pass_match = hmac.compare_digest(password.strip(), expected_pass.strip())
    return user_match and pass_match


def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Api-Key"),
) -> Dict[str, Any]:
    """
    Dépendance FastAPI sécurisée injectant l'administrateur authentifié :
    1. Vérification prioritaire du jeton Bearer JWT.
    2. Fallback sécurisé sur clé d'API système `X-Admin-Api-Key` pour les scripts automatisés.
    """
    # 1. Validation du jeton JWT Bearer
    if credentials and credentials.scheme.lower() == "bearer":
        payload = decode_access_token(credentials.credentials)
        return {
            "sub": payload.get("sub"),
            "name": payload.get("name", "Admin MEDIZY"),
            "role": payload.get("role", "admin"),
            "auth_type": "jwt",
        }

    # 2. Validation de la clé d'API d'urgence ou d'orchestration
    expected_key = os.environ.get("ADMIN_API_KEY", SYSTEM_ADMIN_KEY)
    if x_admin_key and hmac.compare_digest(x_admin_key.strip(), expected_key.strip()):
        return {
            "sub": "system@medizy.dz",
            "name": "Service Orchestrateur MEDIZY",
            "role": "system",
            "auth_type": "api_key",
        }

    # 3. Refus d'accès si aucune méthode valide n'est fournie
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise. Veuillez fournir un jeton Bearer JWT valide (en-tête Authorization) ou une clé API valide.",
        headers={"WWW-Authenticate": "Bearer"},
    )
