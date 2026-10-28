#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test en direct du module back-office de modération MEDIZY."""

import json
import urllib.request

API_BASE = "http://127.0.0.1:8000"


def run_moderation_tests():
    print("=== TEST 0: Authentification JWT Administrateur (POST /api/v1/admin/auth/login) ===")
    login_payload = {
        "username": "admin@medizy.dz",
        "password": "MedizyAdmin2026!",
    }
    login_req = urllib.request.Request(
        f"{API_BASE}/api/v1/admin/auth/login",
        data=json.dumps(login_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(login_req) as resp:
        token_data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        jwt_token = token_data["access_token"]
        print(f"Jeton JWT émis pour: {token_data['admin_name']} (Rôle: {token_data['role']})")
        print(f"Validité: {token_data['expires_in']}s (24 heures)")
        print(f"En-têtes Rate-Limit: Limit={resp.headers.get('X-RateLimit-Limit')}, Remaining={resp.headers.get('X-RateLimit-Remaining')}")

    jwt_headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }

    print("\n=== TEST 1: Soumission d'une contribution citoyenne ===")
    sugg_payload = {
        "name": "Clinique Internationale Les Oliviers Alger",
        "type": "Clinique",
        "wilaya": "Alger",
        "commune": "El Mouradia",
        "address": "Chemin Sidi Yahia",
        "phone": "021 69 11 22",
        "google_maps_url": "https://maps.google.com/?q=36.738910,3.048220",
        "submitter_name": "Dr. Nadia L.",
        "submitter_notes": "Clinique chirurgicale avec urgences ouvertes 24h/24.",
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/facilities/suggest",
        data=json.dumps(sugg_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        sugg_data = json.loads(resp.read().decode())
        sugg_id = sugg_data["suggestion_id"]
        print(f"HTTP Status: {resp.status}")
        print(f"Suggestion créée ID {sugg_id} | Statut: {sugg_data['status']}")
        print(f"Coordonnées extraites: {sugg_data['parsed_coordinates']}")

    print("\n=== TEST 2: Liste administrative des suggestions en attente (GET /api/v1/admin/suggestions) ===")
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/admin/suggestions?status=PENDING",
        headers=jwt_headers,
    )
    with urllib.request.urlopen(req) as resp:
        list_data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        print(f"Total en attente de modération : {list_data['total']}")
        print(f"Rate-Limit headers: Remaining={resp.headers.get('X-RateLimit-Remaining')}")
        for s in list_data["data"][:3]:
            dup = f" [Alerte doublon ID {s['matched_facility_id']}]" if s.get("matched_facility_id") else ""
            print(f"  • ID {s['id']}: {s['name']} ({s['wilaya']}) — Statut: {s['status']}{dup}")

    print(f"\n=== TEST 3: Approbation administrative (POST /api/v1/admin/suggestions/{sugg_id}/approve) ===")
    appr_payload = {
        "moderator_name": "Dr. Benali (Directeur DSP)",
        "moderation_comment": "Établissement contrôlé et conforme au répertoire national.",
        "override_type": "Clinique",
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/admin/suggestions/{sugg_id}/approve",
        data=json.dumps(appr_payload).encode("utf-8"),
        headers=jwt_headers,
    )
    with urllib.request.urlopen(req) as resp:
        appr_data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        fac = appr_data["facility"]
        print(f"Message: {appr_data['message']}")
        print(f"Nouvelle structure créée ID {appr_data['created_facility_id']} :")
        print(f"  • Nom: {fac['name']}")
        print(f"  • Typologie: {fac['type']}")
        print(f"  • Source: {fac['source']}")
        print(f"  • Est vérifié: {fac['is_verified']}")
        print(f"  • Badge: {fac['badge']['label']}")

    print("\n=== TEST 4: Rejet motivé d'une suggestion de test ===")
    # Création d'une suggestion fantaisiste pour test de rejet
    fake_req = urllib.request.Request(
        f"{API_BASE}/api/v1/facilities/suggest",
        data=json.dumps({
            "name": "Dispensaire Fermé 1999",
            "wilaya": "Alger",
            "address": "Rue Principale Ancienne",
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(fake_req) as resp:
        fake_id = json.loads(resp.read().decode())["suggestion_id"]

    rej_payload = {
        "reason": "Établissement fermé définitivement depuis plusieurs années.",
        "moderator_name": "Dr. Benali (Directeur DSP)",
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/admin/suggestions/{fake_id}/reject",
        data=json.dumps(rej_payload).encode("utf-8"),
        headers=jwt_headers,
    )
    with urllib.request.urlopen(req) as resp:
        rej_data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        print(f"Suggestion {fake_id} rejetée avec succès :")
        print(f"  • Statut: {rej_data['status']}")
        print(f"  • Motif : {rej_data['reason']}")


if __name__ == "__main__":
    run_moderation_tests()
