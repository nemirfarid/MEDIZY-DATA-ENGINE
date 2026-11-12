"""
medizy_pipeline.ai — Module d'Intelligence Artificielle MEDIZY
=============================================================
Fournit un service centralisé pour interroger le modèle Gemini (Google GenAI)
via le SDK officiel `google-genai`.

Exports principaux :
    GeminiService      — Classe principale du service IA.
    GeminiConversation — Gestion de la conversation multi-tours.
    get_gemini_service — Singleton compatible FastAPI Depends().
    GeminiServiceError — Exception métier du service.
"""

from .ai_argon_service import (
    GeminiConversation,
    GeminiService,
    GeminiServiceError,
    get_gemini_service,
)

__all__ = [
    "GeminiService",
    "GeminiConversation",
    "GeminiServiceError",
    "get_gemini_service",
]
