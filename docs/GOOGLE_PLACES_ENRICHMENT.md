# Pipeline d'enrichissement Google Maps pour Medizy

## Objectif
Enrichir la base de données SQLite `sante_dz_bundled.db` avec des entités médicales
manquantes (cliniques, pharmacies de garde, laboratoires, cabinets) en utilisant
l'API Google Places (Nearby Search + Place Details).

## Critères stricts d'extraction

### Requête type
```
"[Catégorie] [Commune] [Wilaya] Algérie"
```
Exemples :
- "Cabinet cardiologie Mostaganem"
- "Pharmacie de garde Oran"
- "Laboratoire analyses médicales Alger"
- "Clinique privée Constantine"

### Champs obligatoires normalisés
| Champ | Type | Description |
|-------|------|-------------|
| `nom` | TEXT | Nom de l'établissement |
| `categorie` | TEXT | Catégorie normalisée (pharmacie, clinique, laboratoire, etc.) |
| `adresse_exacte` | TEXT | Adresse complète |
| `wilaya` | TEXT | Nom de la wilaya |
| `commune` | TEXT | Nom de la commune |
| `telephone` | TEXT | Format algérien (05/06/07/02x), sans espaces |
| `latitude` | REAL | Latitude WGS84 |
| `longitude` | REAL | Longitude WGS84 |
| `place_id` | TEXT | Identifiant Google Places (unique) |
| `horaires_ouverture` | TEXT | JSON des horaires d'ouverture |

## Pipeline d'enrichissement

### Étape 1 : Extraction via Google Places API
```python
# Script: enrich_google_places.py
# Utilise Google Places API Nearby Search + Place Details
# Pour chaque wilaya/commune × catégorie :
#   - Requête Nearby Search dans un rayon de 5 km autour du chef-lieu
#   - Pagination (next_page_token) jusqu'à épuisement
#   - Extraction des champs via Place Details API
```

### Étape 2 : Normalisation des données
- Nettoyage des numéros de téléphone (format 05/06/07/02x)
- Normalisation des catégories (lowercase, sans accents)
- Validation des coordonnées GPS (lat: 18-38°N, lon: -9 à +12°E pour l'Algérie)
- Conversion des horaires en JSON structuré

### Étape 3 : Dédoublonnage (Upsert SQLite)
```sql
-- Clé de dédoublonnage : proximité GPS (< 30m) OU correspondance téléphone stricte
INSERT INTO facilities (...)
SELECT ... FROM incoming
WHERE NOT EXISTS (
  SELECT 1 FROM facilities f
  WHERE (
    -- Proximité GPS < 30m (approx. 0.00027° lat/lon)
    (ABS(f.latitude - incoming.latitude) < 0.00027
     AND ABS(f.longitude - incoming.longitude) < 0.00027)
    OR
    -- Correspondance téléphone stricte
    (f.telephone IS NOT NULL AND f.telephone = incoming.telephone AND incoming.telephone != '')
  )
);
```

### Étape 4 : Mise à jour de la base embarquée
1. Exécuter le script d'enrichissement sur la base `sante_dz_bundled.db`
2. Vérifier le COUNT(*) et la couverture des 58 wilayas
3. Copier la base mise à jour dans `assets/data/sante_dz_bundled.db`
4. Rebuild l'APK

## Script Python d'enrichissement (template)

```python
import requests
import sqlite3
import json
import time

API_KEY = "YOUR_GOOGLE_PLACES_API_KEY"
DB_PATH = "assets/data/sante_dz_bundled.db"

CATEGORIES = [
    "pharmacie", "clinique", "laboratoire", "cabinet médical",
    "dentiste", "centre d'imagerie médicale", "centre de radiologie",
    "hôpital", "polyclinique", "médecin généraliste",
]

WILAYAS = [
    # (code, nom, lat_chef_lieu, lon_chef_lieu)
    ("16", "Alger", 36.7538, 3.0588),
    ("31", "Oran", 35.6971, -0.6308),
    ("25", "Constantine", 36.3650, 6.6147),
    ("27", "Mostaganem", 35.9311, 0.0892),
    # ... 58 wilayas
]

def search_nearby(lat, lon, keyword, radius=5000):
    """Recherche Nearby Places via Google Places API."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lon}",
        "radius": radius,
        "keyword": keyword,
        "language": "fr",
        "key": API_KEY,
    }
    results = []
    while True:
        resp = requests.get(url, params=params)
        data = resp.json()
        results.extend(data.get("results", []))
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(2)  # Délai obligatoire pour next_page_token
        params = {"pagetoken": token, "key": API_KEY}
    return results

def get_place_details(place_id):
    """Récupère les détails complets d'un lieu."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,international_phone_number,"
                  "geometry,opening_hours,types,url",
        "language": "fr",
        "key": API_KEY,
    }
    resp = requests.get(url, params=params)
    return resp.json().get("result", {})

def normalize_phone(phone):
    """Normalise le numéro de téléphone au format algérien."""
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("213"):
        digits = "0" + digits[3:]
    if len(digits) == 9 and digits[0] in "567":
        digits = "0" + digits
    return digits if len(digits) == 10 else None

def upsert_facilities(conn, facilities):
    """Insère les nouvelles entités sans doublons (proximité GPS ou téléphone)."""
    cursor = conn.cursor()
    inserted = 0
    for f in facilities:
        # Vérifier les doublons
        cursor.execute("""
            SELECT 1 FROM facilities
            WHERE (ABS(latitude - ?) < 0.00027 AND ABS(longitude - ?) < 0.00027)
               OR (telephone IS NOT NULL AND telephone = ? AND telephone != '')
            LIMIT 1
        """, (f["latitude"], f["longitude"], f["telephone"]))
        if cursor.fetchone():
            continue  # Doublon détecté, skip

        cursor.execute("""
            INSERT INTO facilities (nom, categorie, wilaya, wilaya_code, commune,
                                    adresse, telephone, latitude, longitude, source, place_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'google_places', ?)
        """, (
            f["nom"], f["categorie"], f["wilaya"], f["wilaya_code"], f["commune"],
            f["adresse"], f["telephone"], f["latitude"], f["longitude"], f["place_id"],
        ))
        inserted += 1
    conn.commit()
    return inserted

def main():
    conn = sqlite3.connect(DB_PATH)
    total_inserted = 0

    for code, nom, lat, lon in WILAYAS:
        for cat in CATEGORIES:
            keyword = f"{cat} {nom}"
            results = search_nearby(lat, lon, keyword)
            facilities = []
            for r in results:
                details = get_place_details(r["place_id"])
                geom = details.get("geometry", {}).get("location", {})
                phone = normalize_phone(details.get("formatted_phone_number") or
                                        details.get("international_phone_number"))
                facilities.append({
                    "nom": details.get("name", r.get("name")),
                    "categorie": cat,
                    "wilaya": nom,
                    "wilaya_code": code,
                    "commune": r.get("vicinity", "").split(",")[0].strip(),
                    "adresse": details.get("formatted_address", r.get("vicinity")),
                    "telephone": phone,
                    "latitude": geom.get("lat", r.get("geometry", {}).get("location", {}).get("lat")),
                    "longitude": geom.get("lng", r.get("geometry", {}).get("location", {}).get("lng")),
                    "place_id": r["place_id"],
                })
            inserted = upsert_facilities(conn, facilities)
            total_inserted += inserted
            print(f"[{code} {nom}] {cat}: {len(results)} trouvés, {inserted} insérés")
            time.sleep(1)  # Rate limiting

    conn.close()
    print(f"\nTotal inséré : {total_inserted}")

if __name__ == "__main__":
    main()
```

## Notes importantes
- Respecter les conditions d'utilisation de Google Places API (pas de scraping massif)
- Utiliser les clés API avec restrictions (IP/domaine)
- Prévoir un budget quotidien pour les appels API
- Vérifier la couverture des 58 wilayas après chaque exécution
- Ne jamais écraser silencieusement une information existante avec une info moins fiable
- Conserver la provenance au niveau du champ (source = 'google_places')
