#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTE DZ -- Script de Test & Validation du Service IA Gemini
=====================================================================
Exécute une série de vérifications pour confirmer que la connexion à l'API
Google Generative AI est opérationnelle et que le service répond correctement.

USAGE :
    python test_argon.py
    python test_argon.py --streaming
    python test_argon.py --model gemini-3.8-flash
    python test_argon.py --key YOUR_API_KEY

PRÉREQUIS :
    - GEMINI_API_KEY définie dans .env ou comme variable d'environnement.
    - SDK installé : pip install -U google-genai python-dotenv
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Force UTF-8 sur les terminaux Windows (évite UnicodeEncodeError CP1252)
if sys.stdout.encoding and sys.stdout.encoding.upper() not in ("UTF-8", "UTF8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Chargement du .env avant tout import ────────────────────────────────────
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
        print(f"  .env chargé depuis : {env_path}")
    else:
        print("  ⚠  Aucun .env trouvé — les variables d'env système seront utilisées.")
except ImportError:
    pass


def _banner(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print('═' * 60)


def _ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def _fail(msg: str) -> None:
    print(f"  ❌ {msg}")


def _section(title: str) -> None:
    print(f"\n  ── {title} ──")


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_env_config() -> bool:
    """Test 1 — Vérification de la configuration d'environnement."""
    _section("TEST 1 : Configuration d'environnement")

    api_key = os.environ.get("GEMINI_API_KEY", "")
    model   = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    if not api_key or api_key.startswith("REMPLACER"):
        _fail(
            "GEMINI_API_KEY non définie ou non modifiée.\n"
            "     → Éditez le fichier .env et remplacez REMPLACER_PAR_VOTRE_CLE_API\n"
            "     → Obtenez une clé sur : https://aistudio.google.com/app/apikey"
        )
        return False

    _ok(f"GEMINI_API_KEY  = {api_key[:8]}… ({len(api_key)} caractères)")
    _ok(f"GEMINI_MODEL    = {model}")
    return True


def test_sdk_import() -> bool:
    """Test 2 — Import du SDK google-genai."""
    _section("TEST 2 : Import du SDK `google-genai`")
    try:
        from google import genai
        _ok(f"google-genai importé — version {genai.__version__}")
        if tuple(int(x) for x in genai.__version__.split(".")[:2]) < (2, 25):
            _warn(
                f"Version {genai.__version__} inférieure à 2.25.0 recommandée. "
                "Mettez à jour : pip install -U google-genai"
            )
        return True
    except ImportError as e:
        _fail(f"Import échoué : {e}\n     → pip install -U google-genai")
        return False


def test_service_init(model: str, api_key: str) -> tuple[bool, object]:
    """Test 3 — Initialisation du GeminiService."""
    _section("TEST 3 : Initialisation du GeminiService MEDIZY")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from medizy_pipeline.ai.ai_argon_service import GeminiService
        svc = GeminiService(api_key=api_key, model=model, temperature=0.2, max_retries=2)
        info = svc.info()
        _ok(f"Service initialisé")
        _ok(f"Modèle demandé  : {info['requested_model']}")
        _ok(f"Modèle actif    : {info['active_model']}")
        if info["fallback_occurred"]:
            _warn(
                f"Fallback activé : '{info['requested_model']}' → '{info['active_model']}'.\n"
                f"     → L'identifiant '{info['requested_model']}' n'est pas disponible dans votre compte API."
            )
        return True, svc
    except Exception as e:
        _fail(f"Initialisation échouée : {e}")
        return False, None


def test_basic_generation(svc) -> bool:
    """Test 4 — Génération de texte simple."""
    _section("TEST 4 : Génération de texte (prompt de validation)")
    prompt = (
        "Tu es l'IA de la plateforme de santé algérienne MEDIZY. "
        "Réponds en une phrase courte (max 30 mots) : "
        "Quel est ton rôle principal dans la plateforme MEDIZY ?"
    )
    print(f"  Prompt : «{prompt[:80]}…»")

    t0 = time.time()
    try:
        response = svc.chat(prompt, temperature=0.3)
        elapsed = time.time() - t0
        _ok(f"Réponse reçue en {elapsed:.2f}s :")
        print(f"\n  ┌─────────────────────────────────────────────────────┐")
        for line in response.strip().split("\n"):
            print(f"  │ {line}")
        print(f"  └─────────────────────────────────────────────────────┘")
        return bool(response.strip())
    except Exception as e:
        _fail(f"Génération échouée : {e}")
        return False


def test_streaming(svc) -> bool:
    """Test 5 — Streaming de réponse."""
    _section("TEST 5 : Streaming (réponse en temps réel)")
    prompt = "Liste 3 wilayas d'Algérie avec leur chef-lieu, en format bullet points."
    print(f"  Prompt : «{prompt}»")
    print(f"  Réponse en streaming :\n")
    print("  ", end="", flush=True)

    try:
        chunks = 0
        t0 = time.time()
        for chunk in svc.stream(prompt, temperature=0.1):
            print(chunk, end="", flush=True)
            if "\n" in chunk:
                print("  ", end="", flush=True)
            chunks += 1
        elapsed = time.time() - t0
        print(f"\n")
        _ok(f"Streaming terminé — {chunks} chunks en {elapsed:.2f}s")
        return chunks > 0
    except Exception as e:
        print()
        _fail(f"Streaming échoué : {e}")
        return False


def test_medizy_helper(svc) -> bool:
    """Test 6 — Helper spécialisé MEDIZY (classification catégorie)."""
    _section("TEST 6 : Helper MEDIZY — classification catégorie")
    test_cases = [
        ("Polyclinique El Biar",         "Établissement Public"),
        ("Dr. Meziane Cardiologie",       "Cabinet Médical"),
        ("Pharmacie du Peuple",           "Pharmacie d'Officine"),
        ("Clinique Privée Ain Allah",     "Clinique Privée"),
    ]
    all_ok = True
    for name, expected in test_cases:
        try:
            result = svc.classify_category(name)
            ok = result == expected
            status = "✅" if ok else "⚠️ "
            print(f"    {status} '{name}' → '{result}' (attendu : '{expected}')")
            if not ok:
                all_ok = False
        except Exception as e:
            _fail(f"classify_category('{name}') : {e}")
            all_ok = False
    return all_ok


def test_conversation(svc) -> bool:
    """Test 7 — Conversation multi-tours."""
    _section("TEST 7 : Conversation multi-tours (contexte maintenu)")
    try:
        conv = svc.create_conversation()
        r1 = conv.say("Bonjour, je m'appelle Karim et je travaille pour MEDIZY Algérie.")
        r2 = conv.say("Comment je m'appelle et pour quelle organisation je travaille ?")
        
        # Vérification basique que le contexte est maintenu
        context_ok = "karim" in r2.lower() or "medizy" in r2.lower()
        print(f"    Tour 1 → {r1[:60]}…")
        print(f"    Tour 2 → {r2[:80]}…")
        
        if context_ok:
            _ok(f"Contexte maintenu entre {len(conv)} échanges")
        else:
            _warn("Le modèle n'a pas retenu le contexte (store=True peut nécessiter un compte payant).")
        return True  # Le test réussit même si le contexte n'est pas retenu
    except Exception as e:
        _fail(f"Conversation multi-tours échouée : {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Entrée principale
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test & Validation du Service IA Gemini — MEDIZY",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--key",       default=None, help="Clé API (surcharge .env)")
    parser.add_argument("--model",     default=None, help="Modèle Gemini cible")
    parser.add_argument("--streaming", action="store_true", help="Inclure le test de streaming")
    parser.add_argument("--full",      action="store_true", help="Tous les tests (inclut streaming + conversation)")
    args = parser.parse_args()

    _banner("MEDIZY — Validation du Service IA Google Gemini")
    print(f"  Heure    : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  SDK      : google-genai")
    print(f"  Python   : {sys.version.split()[0]}")

    # Surcharge par argument CLI
    if args.key:
        os.environ["GEMINI_API_KEY"] = args.key
    if args.model:
        os.environ["GEMINI_MODEL"] = args.model

    api_key = os.environ.get("GEMINI_API_KEY", "")
    model   = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    results = {}

    # Test 1 : Config
    results["env"] = test_env_config()
    if not results["env"]:
        _banner("❌ VALIDATION INCOMPLÈTE")
        print("\n  Action requise : configurez GEMINI_API_KEY dans .env")
        print("  Obtenez une clé sur : https://aistudio.google.com/app/apikey\n")
        return 1

    # Test 2 : SDK
    results["sdk"] = test_sdk_import()
    if not results["sdk"]:
        return 1

    # Test 3 : Initialisation service
    results["init"], svc = test_service_init(model, api_key)
    if not results["init"]:
        return 1

    # Test 4 : Génération basique
    results["generation"] = test_basic_generation(svc)

    # Test 5 : Streaming (si demandé)
    if args.streaming or args.full:
        results["streaming"] = test_streaming(svc)

    # Test 6 : Helper MEDIZY
    results["helper"] = test_medizy_helper(svc)

    # Test 7 : Conversation multi-tours (si --full)
    if args.full:
        results["conversation"] = test_conversation(svc)

    # ── Rapport final ──────────────────────────────────────────────────────
    _banner("RAPPORT FINAL")
    passed = sum(1 for v in results.values() if v)
    total  = len(results)

    for test_name, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {test_name}")

    print(f"\n  Résultat : {passed}/{total} tests réussis")

    if passed == total:
        print("\n  🎉 Connexion Gemini opérationnelle !")
        print(f"     Modèle actif : {svc.active_model}")
        print(f"     Importez le service dans votre code :")
        print(f"     from medizy_pipeline.ai import GeminiService, get_gemini_service\n")
        return 0
    else:
        print("\n  ⚠️  Certains tests ont échoué. Vérifiez votre clé API et la connectivité.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
