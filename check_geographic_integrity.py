import os
import sys
import json
from medizy_search import MedizySearchEngine, haversine_distance

SANDBOX_DB = r"D:\SANTE_DZ_EXPORTS\medizy_scraper_sandbox.db"

def verify_geographic_integrity():
    engine = MedizySearchEngine(db_path=SANDBOX_DB)
    results = {}

    # 1. Nearby Alger (lat: 36.7538, lon: 3.0588, radius: 10 km)
    alger_res = engine.search(latitude=36.7538, longitude=3.0588, radius_km=10.0, limit=50)
    alger_wilayas = set(p["wilaya"] for p in alger_res.results)
    alger_coords_ok = all(36.5 <= p["latitude"] <= 37.0 and 2.8 <= p["longitude"] <= 3.3 for p in alger_res.results)
    results["alger"] = {
        "total_in_radius": alger_res.total_count,
        "returned_sample_count": len(alger_res.results),
        "wilayas_found": list(alger_wilayas),
        "coords_plausible": alger_coords_ok
    }

    # 2. Nearby Oran (lat: 35.6987, lon: -0.6349, radius: 10 km)
    oran_res = engine.search(latitude=35.6987, longitude=-0.6349, radius_km=10.0, limit=50)
    oran_wilayas = set(p["wilaya"] for p in oran_res.results)
    oran_coords_ok = all(35.5 <= p["latitude"] <= 36.0 and -1.0 <= p["longitude"] <= -0.4 for p in oran_res.results)
    results["oran"] = {
        "total_in_radius": oran_res.total_count,
        "returned_sample_count": len(oran_res.results),
        "wilayas_found": list(oran_wilayas),
        "coords_plausible": oran_coords_ok
    }

    # 3. Nearby Constantine (lat: 36.3650, lon: 6.6147, radius: 10 km)
    const_res = engine.search(latitude=36.3650, longitude=6.6147, radius_km=10.0, limit=50)
    const_wilayas = set(p["wilaya"] for p in const_res.results)
    const_coords_ok = all(36.1 <= p["latitude"] <= 36.6 and 6.3 <= p["longitude"] <= 6.9 for p in const_res.results)
    results["constantine"] = {
        "total_in_radius": const_res.total_count,
        "returned_sample_count": len(const_res.results),
        "wilayas_found": list(const_wilayas),
        "coords_plausible": const_coords_ok
    }

    # 4. Nearby Adrar Centre (lat: 27.9598, lon: -0.2481, radius: 30 km)
    adrar_res = engine.search(latitude=27.9598, longitude=-0.2481, radius_km=30.0, limit=200)
    adrar_wilayas = set(p["wilaya"] for p in adrar_res.results)
    northern_wilayas = {"Alger", "Oran", "Constantine", "Annaba", "Batna", "Relizane", "Bouira", "Tizi Ouzou", "Sétif", "Guelma", "Bordj Bou Arréridj"}
    leakage_north_in_adrar = northern_wilayas.intersection(adrar_wilayas)
    results["adrar"] = {
        "total_in_radius": adrar_res.total_count,
        "returned_sample_count": len(adrar_res.results),
        "wilayas_found": list(adrar_wilayas),
        "northern_leakage_detected": list(leakage_north_in_adrar),
        "is_clean": len(leakage_north_in_adrar) == 0
    }

    # 5. Nearby Erroneous Centroid (lat: 28.09487, lon: 1.66544, radius: 10 km)
    centroid_res = engine.search(latitude=28.09487, longitude=1.66544, radius_km=10.0, limit=50)
    results["erroneous_centroid_point"] = {
        "coords": [28.09487, 1.66544],
        "total_in_radius_10km": centroid_res.total_count,
        "structures_remaining": [p["nom"] for p in centroid_res.results]
    }

    engine.close()
    return results

if __name__ == "__main__":
    res = verify_geographic_integrity()
    out_file = r"D:\SANTE_DZ_EXPORTS\reports\geographic_integrity_verification.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(f"Rapport d'intégrité géographique écrit dans {out_file}")
    print(json.dumps(res, indent=2, ensure_ascii=True))
