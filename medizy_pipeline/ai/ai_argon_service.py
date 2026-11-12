#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Service IA Centralisé (Google Gemini)
==========================================================
Module réutilisable pour interroger le modèle Gemini via le SDK officiel
`google-genai`. Conçu pour être importé dans FastAPI, scripts CLI ou notebooks.

CONFIGURATION REQUISE (.env à la racine du projet) :
    GEMINI_API_KEY=<votre_clé_api_google_ai_studio>
    GEMINI_MODEL=gemini-3.8-flash   # Modèle par défaut (le plus récent disponible)

USAGE MINIMAL :
    from medizy_pipeline.ai.ai_argon_service import GeminiService
    svc = GeminiService()
    print(svc.chat("Quelle est la capitale de l'Algérie ?"))

NOTE sur "Gemini 4 Argon" :
    Cet identifiant n'est pas encore disponible publiquement dans l'API Google
    Generative AI. Le service utilise le modèle configuré dans GEMINI_MODEL
    (défaut : gemini-3.8-flash) avec un fallback automatique vers les modèles
    disponibles si l'identifiant personnalisé échoue.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Generator, Iterator, List, Optional

# ─── Chargement des variables d'environnement ──────────────────────────────
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).parent.parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file, override=False)
    else:
        load_dotenv(override=False)  # cherche dans le répertoire courant
except ImportError:
    pass  # python-dotenv optionnel si env déjà injectées

log = logging.getLogger("medizy.ai.gemini_service")

# ─── Constantes et modèles disponibles ────────────────────────────────────

# Ordre de priorité du fallback automatique :
# 1. Modèle demandé (GEMINI_MODEL env)
# 2. gemini-3.8-flash     — Polyvalent, 1M tokens, multimodal, agentic
# 3. gemini-3.1-pro-preview — Raisonnement complexe, code, recherche
# 4. gemini-3.5-flash-lite  — Haute fréquence, coût minimal
FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash-lite",
]

# Paramètres par défaut
DEFAULT_TEMPERATURE_CODE  = 0.2   # Logique stricte, code, SQL
DEFAULT_TEMPERATURE_CREATIVE = 0.7  # Génération créative, résumés
DEFAULT_MAX_TOKENS       = 8192
DEFAULT_RETRY_ATTEMPTS   = 3
DEFAULT_RETRY_DELAY_S    = 2.0


class GeminiServiceError(RuntimeError):
    """Erreur levée quand le service IA est indisponible ou mal configuré."""
    pass


class GeminiService:
    """
    Service IA centralisé MEDIZY — Wrapper autour du SDK `google-genai`.

    Fonctionnalités :
    - Initialisation automatique depuis les variables d'environnement.
    - Fallback automatique vers un modèle disponible si l'identifiant demandé
      n'est pas trouvé dans le catalogue de l'API.
    - Méthodes synchrones (chat, generate) et streaming.
    - Retry automatique avec backoff exponentiel en cas de quota / surcharge.
    - Gestion du contexte multi-tours via `previous_interaction_id`.
    - Mode "code" (température basse) et "creative" (température haute).

    Paramètres :
        api_key    : Clé API Google AI Studio. Priorité : arg > env GEMINI_API_KEY.
        model      : Identifiant du modèle. Priorité : arg > env GEMINI_MODEL.
        temperature: Température de génération (0.0–2.0). Défaut : 0.2.
        max_retries: Nombre de tentatives automatiques en cas d'erreur.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE_CODE,
        max_retries: int = DEFAULT_RETRY_ATTEMPTS,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise GeminiServiceError(
                "❌ GEMINI_API_KEY non définie.\n"
                "Ajoutez-la dans votre fichier .env :\n"
                "    GEMINI_API_KEY=votre_cle_api\n"
                "Obtenez une clé sur : https://aistudio.google.com/app/apikey"
            )

        # Lecture du modèle cible (peut être un identifiant personnalisé comme
        # "gemini-4-argon" — le fallback gérera l'indisponibilité automatiquement)
        self.requested_model = model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        self.active_model: str = self.requested_model
        self.temperature = temperature
        self.max_retries = max_retries

        # Initialisation du client SDK officiel
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise GeminiServiceError(
                "SDK `google-genai` introuvable. Installez-le avec :\n"
                "    pip install -U google-genai"
            )

        # Résolution du modèle (avec fallback automatique)
        self.active_model = self._resolve_model()
        log.info(
            f"GeminiService initialisé — modèle actif : {self.active_model} "
            f"(demandé : {self.requested_model}) — température : {self.temperature}"
        )

    # ─── Résolution du modèle avec fallback ───────────────────────────────

    def _resolve_model(self) -> str:
        """
        Tente d'utiliser le modèle demandé. Si indisponible (identifiant
        inconnu ou expérimental), bascule vers le premier modèle disponible
        dans FALLBACK_MODELS.
        """
        candidates = [self.requested_model] + [
            m for m in FALLBACK_MODELS if m != self.requested_model
        ]

        for candidate in candidates:
            try:
                # Appel minimal de validation (1 token max)
                self._client.interactions.create(
                    model=candidate,
                    input="ping",
                    generation_config={"max_output_tokens": 1},
                )
                if candidate != self.requested_model:
                    log.warning(
                        f"Modèle '{self.requested_model}' indisponible → "
                        f"bascule vers '{candidate}'."
                    )
                return candidate
            except Exception as e:
                log.debug(f"Modèle '{candidate}' rejeté : {e}")
                continue

        # Dernier recours : retourner le modèle demandé sans validation
        log.warning(
            f"Impossible de valider un modèle. "
            f"Utilisation de '{self.requested_model}' sans garantie."
        )
        return self.requested_model

    # ─── Méthode principale : génération synchrone ───────────────────────

    def chat(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        previous_interaction_id: Optional[str] = None,
        store: bool = True,
    ) -> str:
        """
        Envoie un prompt au modèle Gemini et retourne la réponse complète.

        Args:
            prompt               : Texte de l'utilisateur.
            system_instruction   : Instruction système optionnelle (rôle de l'IA).
            temperature          : Surcharge la température du service.
            max_tokens           : Nombre maximum de tokens en sortie.
            previous_interaction_id: ID d'une interaction précédente (contexte multi-tours).
            store                : Si False, la conversation n'est pas conservée côté serveur.

        Returns:
            Texte de la réponse du modèle.

        Raises:
            GeminiServiceError   : En cas d'échec après tous les retries.
        """
        kwargs: dict = {
            "model": self.active_model,
            "input": prompt,
            "generation_config": {
                "temperature": temperature if temperature is not None else self.temperature,
                "max_output_tokens": max_tokens,
            },
            "store": store,
        }
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if previous_interaction_id:
            kwargs["previous_interaction_id"] = previous_interaction_id

        return self._execute_with_retry("chat", kwargs)

    # ─── Streaming ────────────────────────────────────────────────────────

    def stream(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        previous_interaction_id: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Génère la réponse en streaming (Server-Sent Events).
        Yield un chunk de texte à chaque événement `step.delta`.

        Exemple :
            for chunk in svc.stream("Explique PostGIS en 3 points"):
                print(chunk, end="", flush=True)
        """
        from google import genai

        kwargs: dict = {
            "model": self.active_model,
            "input": prompt,
            "stream": True,
            "generation_config": {
                "temperature": temperature if temperature is not None else self.temperature,
                "max_output_tokens": max_tokens,
            },
        }
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if previous_interaction_id:
            kwargs["previous_interaction_id"] = previous_interaction_id

        for attempt in range(1, self.max_retries + 1):
            try:
                for event in self._client.interactions.create(**kwargs):
                    if event.event_type == "step.delta":
                        if event.delta.type == "text":
                            yield event.delta.text
                    elif event.event_type == "interaction.completed":
                        usage = getattr(event.interaction, "usage", None)
                        if usage:
                            log.debug(
                                f"Streaming terminé — "
                                f"tokens : in={getattr(usage, 'input_tokens', '?')} "
                                f"out={getattr(usage, 'output_tokens', '?')}"
                            )
                return  # Succès
            except Exception as e:
                if attempt < self.max_retries:
                    delay = DEFAULT_RETRY_DELAY_S * (2 ** (attempt - 1))
                    log.warning(
                        f"Erreur streaming (tentative {attempt}/{self.max_retries}) : {e}. "
                        f"Retry dans {delay:.1f}s…"
                    )
                    time.sleep(delay)
                else:
                    raise GeminiServiceError(
                        f"Échec du streaming après {self.max_retries} tentatives : {e}"
                    ) from e

    # ─── Multi-tours (conversation) ────────────────────────────────────────

    def create_conversation(self) -> "GeminiConversation":
        """
        Crée un objet de conversation multi-tours qui maintient le contexte
        entre plusieurs échanges via `previous_interaction_id`.
        """
        return GeminiConversation(self)

    # ─── Helpers spécialisés MEDIZY ──────────────────────────────────────

    def analyze_facility(self, facility_data: dict) -> str:
        """
        Analyse une fiche établissement MEDIZY et retourne un résumé enrichi.
        Température basse (0.1) pour minimiser les hallucinations.
        """
        prompt = (
            f"Tu es un expert en santé publique algérienne. "
            f"Analyse la fiche d'établissement suivante et retourne un résumé "
            f"structuré (en français) avec : type, spécialités clés, horaires, "
            f"statut (public/privé), et recommandation d'usage patient.\n\n"
            f"Fiche :\n{facility_data}"
        )
        return self.chat(prompt, temperature=0.1)

    def enrich_facility_description(
        self, name: str, categorie: str, commune: str, wilaya: str
    ) -> str:
        """
        Génère une description publique enrichie pour une structure sanitaire.
        Température plus haute (0.5) pour la fluidité du texte.
        """
        prompt = (
            f"Rédige une courte description publique (2-3 phrases, ton professionnel) "
            f"pour la fiche MEDIZY de l'établissement suivant :\n"
            f"- Nom : {name}\n"
            f"- Catégorie : {categorie}\n"
            f"- Commune : {commune}, Wilaya : {wilaya}\n"
            f"La description doit être utile pour un patient cherchant des soins."
        )
        return self.chat(prompt, temperature=0.5)

    def classify_category(self, raw_name: str) -> str:
        """
        Classifie automatiquement un établissement dans une catégorie MEDIZY
        à partir de son nom brut. Température 0.0 pour déterminisme maximal.
        """
        categories = [
            "Établissement Public", "CHU", "EPH", "EPSP", "EHS",
            "Clinique Privée", "Cabinet Médical", "Pharmacie d'Officine",
            "Médecine Spécialisée", "Centre de Diagnostic", "Urgences",
            "Laboratoire", "Cabinet Dentaire", "Opticien", "Autre",
        ]
        prompt = (
            f"Classifie l'établissement de santé algérien suivant dans UNE SEULE "
            f"des catégories listées. Réponds UNIQUEMENT avec le nom exact de la catégorie.\n\n"
            f"Établissement : '{raw_name}'\n\n"
            f"Catégories disponibles :\n" + "\n".join(f"- {c}" for c in categories)
        )
        result = self.chat(prompt, temperature=0.0)
        # Normaliser la réponse
        result = result.strip().strip("-•").strip()
        return result if result in categories else "Autre"

    # ─── Moteur d'exécution avec retry ────────────────────────────────────

    def _execute_with_retry(self, method: str, kwargs: dict) -> str:
        """Exécute un appel API avec retry automatique + backoff exponentiel."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                interaction = self._client.interactions.create(**kwargs)
                text = getattr(interaction, "output_text", None)
                if text is None:
                    # Fallback sur le contenu brut des steps
                    steps = getattr(interaction, "steps", [])
                    texts = []
                    for step in steps:
                        if getattr(step, "type", "") == "model_output":
                            for part in getattr(step, "content", []):
                                if getattr(part, "type", "") == "text":
                                    texts.append(getattr(part, "text", ""))
                    text = "".join(texts)
                return text or ""

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_quota = any(k in err_str for k in ["quota", "rate", "429", "resource_exhausted"])
                is_model = any(k in err_str for k in ["not found", "404", "invalid model"])

                if is_model and self.active_model == self.requested_model:
                    # Modèle invalide → tenter le fallback maintenant
                    log.warning(
                        f"Modèle '{self.active_model}' refusé à l'exécution. "
                        f"Bascule vers le fallback…"
                    )
                    for fallback in FALLBACK_MODELS:
                        if fallback != self.active_model:
                            self.active_model = fallback
                            kwargs["model"] = fallback
                            log.info(f"Nouveau modèle actif : {self.active_model}")
                            break
                    continue

                if attempt < self.max_retries:
                    delay = DEFAULT_RETRY_DELAY_S * (2 ** (attempt - 1))
                    if is_quota:
                        delay = min(delay * 3, 30.0)  # Backoff plus long pour quota
                    log.warning(
                        f"Erreur API (tentative {attempt}/{self.max_retries}) : {e}. "
                        f"Retry dans {delay:.1f}s…"
                    )
                    time.sleep(delay)
                else:
                    break

        raise GeminiServiceError(
            f"Échec après {self.max_retries} tentatives. "
            f"Dernière erreur : {last_error}"
        ) from last_error

    # ─── Informations de diagnostic ───────────────────────────────────────

    def info(self) -> dict:
        """Retourne les informations de configuration du service."""
        return {
            "sdk": "google-genai",
            "requested_model": self.requested_model,
            "active_model": self.active_model,
            "fallback_occurred": self.active_model != self.requested_model,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "api_key_set": bool(self.api_key),
            "api_key_preview": f"{self.api_key[:8]}…" if len(self.api_key) > 8 else "***",
        }

    def __repr__(self) -> str:
        return (
            f"GeminiService(model='{self.active_model}', "
            f"temperature={self.temperature}, retries={self.max_retries})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Objet de conversation multi-tours
# ─────────────────────────────────────────────────────────────────────────────

class GeminiConversation:
    """
    Gère une conversation multi-tours en maintenant le contexte via
    `previous_interaction_id` entre chaque échange.

    Exemple :
        conv = svc.create_conversation()
        conv.say("Bonjour, mon nom est Karim.")
        rep  = conv.say("Comment t'appelles-tu ?")
        # Le modèle se souvient du contexte de la première question.
    """

    def __init__(self, service: GeminiService):
        self._svc = service
        self._last_id: Optional[str] = None
        self.history: List[dict] = []

    def say(
        self,
        message: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Envoie un message et retourne la réponse du modèle."""
        response = self._svc.chat(
            message,
            system_instruction=system_instruction,
            temperature=temperature,
            previous_interaction_id=self._last_id,
        )
        # Note : `previous_interaction_id` nécessite que store=True (défaut).
        # L'ID de la nouvelle interaction est géré côté serveur.
        self.history.append({"role": "user", "text": message})
        self.history.append({"role": "model", "text": response})
        return response

    def reset(self) -> None:
        """Réinitialise le contexte de la conversation."""
        self._last_id = None
        self.history.clear()
        log.info("Contexte de conversation réinitialisé.")

    def __len__(self) -> int:
        return len(self.history) // 2  # Nombre d'échanges complets


# ─────────────────────────────────────────────────────────────────────────────
# Instance singleton pour usage direct dans FastAPI
# ─────────────────────────────────────────────────────────────────────────────

_service_instance: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """
    Retourne l'instance singleton du service Gemini.
    Compatible avec FastAPI Depends().

    Exemple FastAPI :
        from medizy_pipeline.ai.ai_argon_service import get_gemini_service
        @app.post("/ai/analyze")
        def analyze(body: AnalyzeRequest, ai: GeminiService = Depends(get_gemini_service)):
            return {"result": ai.chat(body.prompt)}
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = GeminiService()
    return _service_instance
