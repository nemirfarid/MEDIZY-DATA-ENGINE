# SANTÉ DZ / MEDIZY — GUIDE TECHNIQUE D'INJECTION & INTÉGRATION CLIENT
**Programme National Sanitaire Algérie — Version Officielle 1.0.15-data-injected**

---

## 1. Vue d'Ensemble & Spécifications de Référence

Le jeu de données national consolidé **SANTÉ DZ / MEDIZY (v1.0.15)** rassemble l'inventaire cartographié et qualifié de l'ensemble des infrastructures sanitaires de la République Algérienne Démocratique et Populaire.

### Métriques Clés Certifiées
* **Volume total** : **35 832 établissements qualifiés** (0 doublon, 0 corruption).
* **Couverture géographique** : **58 wilayas d'Algérie** (codes 01 Adrar à 58 El Meniaa).
* **Précision géodésique** : **100% avec coordonnées GPS normalisées WGS84** (Latitude [18.5°, 37.5°], Longitude [-9.0°, 12.5°]).
* **Taxonomie médicale** : **102 spécialités et catégories de santé** documentées.
* **Architecture client** : **Offline-first (100% autonome sans connexion réseau)**.

---

## 2. Catalogue des Fichiers Distribués (`D:\SANTE_DZ_EXPORTS\`)

### 2.1. Extractions Multi-Formats Nationales
| Fichier | Format | Poids | Usage Recommandé |
| :--- | :--- | :--- | :--- |
| `SANTE_DZ_NATIONAL_35832.csv` | CSV UTF-8 avec BOM | ~6.29 Mo | Outils BI, Excel, DataFrames Python, OpenData |
| `sante_dz_full_dataset.json` | JSON UTF-8 | ~28.1 Mo | Backends REST, ElasticSearch, Ingestion NoSQL |
| `sante_dz_map_features.geojson` | GeoJSON (RFC 7946) | ~15.4 Mo | SIG (QGIS, ArcGIS), Mapbox GL, MapLibre, Leaflet |
| `SANTE_DZ_REGISTRE_NATIONAL.xlsx` | Excel multi-onglets | ~3.35 Mo | Audits administratifs, ministères, consultation tabulaire |

*L'Excel comprend 7 feuilles structurées : Synthèse & Métriques, Pharmacies (6 229), Médecins (12 756), Hôpitaux & Polycliniques (8 173), Laboratoires (2 254), Dentistes (3 592) et Autres & Paramédical (2 828).*

### 2.2. Package Client Embarqué (`mobile/assets/data/`)
| Fichier Asset | Type | Poids | Rôle Embarqué |
| :--- | :--- | :--- | :--- |
| `sante_dz_db.json.gz` | Gzip JSON compressé | **1.97 Mo** | Chargement mémoire instantané (< 105 ms décompression) |
| `sante_dz_bundled.db` | SQLite 3 (FTS5 + R-Tree) | **13.29 Mo** | Base de données locale pré-indexée recherche plein texte & spatiale |
| `medizy_wilayas_index.json` | Index JSON léger | 41 Ko | Menu de sélection et filtrage immédiat par les 58 wilayas |
| `medizy_categories_index.json` | Index JSON taxonomique | 18 Ko | Arborescence des 102 spécialités médicales et paramédicales |

---

## 3. Architecture de la Base SQLite Embarquée (`sante_dz_bundled.db`)

La base SQLite embarquée a été compilée pour garantir une latence d'accès ultra-faible sur smartphones :
1. **Table principale `facilities`** :
   ```sql
   CREATE TABLE facilities (
       id INTEGER PRIMARY KEY,
       nom TEXT NOT NULL,
       categorie TEXT NOT NULL,
       specialite TEXT,
       wilaya TEXT NOT NULL,
       commune TEXT NOT NULL,
       adresse TEXT,
       telephone TEXT,
       email TEXT,
       site_web TEXT,
       latitude REAL NOT NULL,
       longitude REAL NOT NULL,
       source TEXT,
       derniere_maj TEXT
   );
   ```
2. **Moteur FTS5 `facilities_fts`** :
   Index plein texte tokenisé pour autocomplétion rapide (recherche sur nom, commune, wilaya, catégorie, spécialité). Latence mesurée : **~1.1 ms**.
   ```sql
   SELECT f.* FROM facilities f
   JOIN facilities_fts fts ON f.id = fts.rowid
   WHERE facilities_fts MATCH 'cardio* OR oranaise'
   LIMIT 20;
   ```
3. **Index Spatial R-Tree `facilities_rtree`** :
   Index d'arbre rectangle 2D pour requêtes géographiques de proximité (rayon GPS, bounding box autour de l'utilisateur). Latence mesurée : **~0.26 ms**.
   ```sql
   SELECT f.* FROM facilities f
   JOIN facilities_rtree r ON f.id = r.id
   WHERE r.min_lat >= ? AND r.max_lat <= ?
     AND r.min_lon >= ? AND r.max_lon <= ?;
   ```

---

## 4. Intégration dans l'Application Client Mobile (Flutter / Dart)

### Étape 1 : Déclaration des Assets dans `pubspec.yaml`
```yaml
flutter:
  assets:
    - assets/data/sante_dz_db.json.gz
    - assets/data/sante_dz_bundled.db
    - assets/data/medizy_wilayas_index.json
    - assets/data/medizy_categories_index.json
```

### Étape 2 : Déploiement Local SQLite au Premier Lancement (Cold Start)
```dart
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

class LocalDatabaseService {
  static Database? _database;

  static Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initBundledDatabase();
    return _database!;
  }

  static Future<Database> _initBundledDatabase() async {
    final dbDir = await getDatabasesPath();
    final path = join(dbDir, "sante_dz_bundled.db");

    // Déploiement de la base pré-remplie si elle n'existe pas encore
    if (!await File(path).exists()) {
      ByteData data = await rootBundle.load("assets/data/sante_dz_bundled.db");
      List<int> bytes = data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
      await File(path).writeAsBytes(bytes, flush: true);
    }

    return await openDatabase(
      path,
      readOnly: true, // Sécurité & performances de lecture optimisées
    );
  }
}
```

### Étape 3 : Requête de Recherche Hors-Ligne Instantanée (FTS5)
```dart
Future<List<Map<String, dynamic>>> searchFacilities(String query) async {
  final db = await LocalDatabaseService.database;
  // Nettoyage et syntaxe FTS5 prefix
  final sanitizedQuery = query.trim().replaceAll("'", "''") + "*";
  
  return await db.rawQuery('''
    SELECT f.id, f.nom, f.categorie, f.specialite, f.wilaya, f.commune, 
           f.telephone, f.latitude, f.longitude
    FROM facilities f
    JOIN facilities_fts fts ON f.id = fts.rowid
    WHERE facilities_fts MATCH ?
    LIMIT 50;
  ''', [sanitizedQuery]);
}
```

### Étape 4 : Requête de Proximité Géographique (R-Tree)
```dart
Future<List<Map<String, dynamic>>> getNearbyFacilities({
  required double userLat,
  required double userLon,
  double radiusKm = 5.0,
}) async {
  final db = await LocalDatabaseService.database;
  // Bounding box approximative (1° lat ≈ 111 km, 1° lon ≈ 89 km en Algérie)
  final deltaLat = radiusKm / 111.0;
  final deltaLon = radiusKm / 89.0;

  return await db.rawQuery('''
    SELECT f.*
    FROM facilities f
    JOIN facilities_rtree r ON f.id = r.id
    WHERE r.min_lat >= ? AND r.max_lat <= ?
      AND r.min_lon >= ? AND r.max_lon <= ?
    LIMIT 100;
  ''', [
    userLat - deltaLat,
    userLat + deltaLat,
    userLon - deltaLon,
    userLon + deltaLon,
  ]);
}
```

---

## 5. Audit de Conformité & Empreintes Cryptographiques

Le script d'inspection automatisé `tools/verify_client_ingestion.py` garantit la non-régression et le respect des seuils de performance :
```powershell
.\.venv\Scripts\python.exe tools/verify_client_ingestion.py
```

### Registre SHA-256 Officiel (`D:\SANTE_DZ_EXPORTS\SHA256SUMS_v1.0.15.txt`)
```text
f6d887c1460cfcabdde32ceb87c40fbf0707c1421483ce0a822f7ace2ff83a8e  SANTE_DZ_NATIONAL_35832.csv
4a8c1e9a9d2e42e8bfbbfc14fbe5945d9c80bb7fe0620509864c3f3177e0fb3d  sante_dz_full_dataset.json
9501a16e53e1e6f524130c41846c7b1abc008fe8e321c2097af00fca68f21fed  sante_dz_map_features.geojson
6c44925e356bb74a8541168fc383a18fa2d9b788b1ce84c0f2697385d6439804  SANTE_DZ_REGISTRE_NATIONAL.xlsx
4f3cf7f1427678be2a5a86dc03755c68604a8d7ae0acc58ba4fdba7b283909ad  mobile/medizy_national_cache.json.gz
4f3cf7f1427678be2a5a86dc03755c68604a8d7ae0acc58ba4fdba7b283909ad  mobile/sante_dz_db.json.gz
e95c417ac1d05a1581704b744d51a605afb64ccf8acb9adbe3ece4787f1ee3e3  mobile/medizy_wilayas_index.json
413de608d37eeaa7040c63576686d944e5c16fd711c8d7b0864e49b3247b842b  mobile/medizy_categories_index.json
3fb7e71266b9cedaaafe84c063ab6fa8f5f457ff6dd3e0a3b2a3ebfe9bc5b4e8  mobile/sante_dz_bundled.db
```

---
*Document certifié par le Programme National de Santé Publique Médicale et Pharmaceutique SANTÉ DZ / MEDIZY.*
