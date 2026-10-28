#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation de l'Observabilité Prometheus et de l'Export NIBRAS MEDIZY.
"""

import json
import urllib.request

API_BASE = "http://127.0.0.1:8000"


def test_observability_and_export():
    print("=== TEST 1 : Exécution de requêtes géospatiales pour alimenter les métriques ===")
    search_url = f"{API_BASE}/api/v1/facilities/search?wilaya=Alger&limit=5"
    with urllib.request.urlopen(search_url) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print(f"  • /search : {data['total']} résultats en {data['execution_time_ms']} ms")

    nearby_url = f"{API_BASE}/api/v1/facilities/nearby?lat=36.75&lon=3.05&radius_km=5&limit=5"
    with urllib.request.urlopen(nearby_url) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print(f"  • /nearby : {data['total']} résultats en {data['execution_time_ms']} ms")

    print("\n=== TEST 2 : Vérification du point d'accès Prometheus (/metrics) ===")
    metrics_url = f"{API_BASE}/metrics"
    with urllib.request.urlopen(metrics_url) as resp:
        assert resp.status == 200
        raw_metrics = resp.read().decode("utf-8")
        print(f"  • Code HTTP /metrics : {resp.status} (Taille : {len(raw_metrics)} octets)")

        # Vérification des indicateurs clés demandés
        indicators = [
            "pending_suggestions_gauge",
            "osm_mirror_failover_total",
            "medizy_geosearch_duration_seconds",
            "medizy_geosearch_requests_total",
        ]
        for ind in indicators:
            if ind in raw_metrics:
                print(f"  [OK] Indicateur detecte dans le flux Prometheus : '{ind}'")
            else:
                print(f"  [FAIL] Indicateur manquant : '{ind}'")
                raise AssertionError(f"Metrique Prometheus manquante: {ind}")

        # Affichage d'extraits pertinents
        print("\n  Extrait des metriques collectees :")
        for line in raw_metrics.splitlines():
            if any(k in line for k in ["pending_suggestions_gauge", "medizy_geosearch", "osm_mirror"]) and not line.startswith("#"):
                print(f"    {line}")

    print("\n=== TEST 3 : Passerelle de synchronisation NIBRAS (GET /api/v1/facilities/export/latest) ===")
    export_url = f"{API_BASE}/api/v1/facilities/export/latest?limit=3"
    with urllib.request.urlopen(export_url) as resp:
        assert resp.status == 200
        exp_data = json.loads(resp.read().decode())
        print(f"  • Elements recus : {exp_data['count']}")
        print(f"  • has_more : {exp_data['has_more']}")
        print(f"  • next_cursor : {exp_data['next_cursor']}")
        print(f"  • sync_timestamp : {exp_data['sync_timestamp']}")

        first_fac = exp_data["facilities"][0]
        print(f"\n  Exemple de fiche synchronisee pour l'agent NIBRAS :")
        print(f"    • ID : #{first_fac['id']}")
        print(f"    • Nom : {first_fac['name']} ({first_fac['type']})")
        print(f"    • Wilaya : {first_fac['wilaya']}")
        print(f"    • Coordonnees : ({first_fac['latitude']}, {first_fac['longitude']})")
        print(f"    • Contexte RAG pre-calcule :")
        print(f"      {first_fac['embedding_context'].encode('ascii', 'replace').decode('ascii')}")

    # Test avec pagination par curseur
    if exp_data["next_cursor"]:
        cursor = exp_data["next_cursor"]
        paged_url = f"{API_BASE}/api/v1/facilities/export/latest?cursor={cursor}&limit=2"
        with urllib.request.urlopen(paged_url) as resp:
            assert resp.status == 200
            paged_data = json.loads(resp.read().decode())
            print(f"\n  [OK] Pagination par curseur ({cursor}) validee : {paged_data['count']} fiches suivantes (IDs: {[f['id'] for f in paged_data['facilities']]})")

    print("\n=== TOUS LES TESTS D'OBSERVABILITÉ ET D'EXPORT SONT VALIDÉS AVEC SUCCÈS ===")


if __name__ == "__main__":
    test_observability_and_export()
