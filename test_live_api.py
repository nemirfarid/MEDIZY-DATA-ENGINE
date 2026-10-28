#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script de test en direct des endpoints de l'API MEDIZY."""

import json
import urllib.request

def run_tests():
    # 1. Test /health
    print("=== 1. TEST /health ===")
    with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        print(json.dumps(data, indent=2))

    # 2. Test /api/v1/facilities/search?wilaya=Alger&limit=2
    print("\n=== 2. TEST /api/v1/facilities/search?wilaya=Alger&limit=2 ===")
    url_search = "http://127.0.0.1:8000/api/v1/facilities/search?wilaya=Alger&limit=2"
    with urllib.request.urlopen(url_search, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        print(f"Total établissements trouvés pour Alger : {data['total']}")
        print(f"Temps d'exécution serveur : {data['execution_time_ms']} ms")
        if data['data']:
            print("Exemple de structure retournée avec badge :")
            print(json.dumps(data['data'][0], indent=2, ensure_ascii=False))

    # 3. Test POST /api/v1/facilities/suggest
    print("\n=== 3. TEST POST /api/v1/facilities/suggest ===")
    payload = {
        "name": "Clinique Médico-Chirurgicale Hydra Test",
        "type": "Clinique",
        "wilaya": "Alger",
        "commune": "Hydra",
        "google_maps_url": "https://maps.google.com/?q=36.745012,3.041055",
        "phone": "021 60 12 34",
        "submitter_name": "Dr. Sofiane",
        "submitter_notes": "Clinique avec bloc opératoire et urgences 24h."
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/facilities/suggest",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        print("Réponse de la suggestion citoyenne :")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    # 4. Test GET /api/v1/facilities/nearby (Rayon spatial 3km)
    print("\n=== 4. TEST /api/v1/facilities/nearby (Rayon spatial 3km) ===")
    url_nearby = "http://127.0.0.1:8000/api/v1/facilities/nearby?lat=36.7525&lon=3.0420&radius_km=3&limit=3"
    with urllib.request.urlopen(url_nearby, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        print(f"Trouvés à proximité de Alger (36.7525, 3.0420) : {data['total']} structures")
        for f in data['data']:
            dist_str = f"{f['distance_meters']:.1f} m" if f['distance_meters'] is not None else "N/A"
            print(f"  • {f['name']} [{f['type']}] — Distance: {dist_str} — Badge: {f['badge']['label']}")

if __name__ == "__main__":
    run_tests()
