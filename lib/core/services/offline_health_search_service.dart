import 'dart:io';
import 'dart:math' as math;
import 'package:sqlite3/sqlite3.dart';
import '../models/health_facility.dart';

/// Service de recherche hors-ligne hybride (FTS5 + R-Tree) - Santé DZ / Medizy
class OfflineHealthSearchService {
  Database? _db;
  bool _isInitialized = false;

  bool get isInitialized => _isInitialized;

  PreparedStatement? _ftsStmt;
  PreparedStatement? _ftsBenchStmt;
  PreparedStatement? _rtreeStmt;
  PreparedStatement? _rtreeExtractStmt;

  /// Initialise la connexion SQLite en mode lecture seule stricte
  void initialize({String? customPath}) {
    if (_isInitialized && _db != null) return;

    final candidatePaths = [
      if (customPath != null) customPath,
      'assets/data/sante_dz_bundled.db',
      r'D:\SANTE_DZ_EXPORTS\mobile\assets\data\sante_dz_bundled.db',
      r'D:\SANTE_DZ_EXPORTS\mobile\sante_dz_bundled.db',
    ];

    String? resolvedPath;
    for (final p in candidatePaths) {
      if (File(p).existsSync()) {
        resolvedPath = p;
        break;
      }
    }

    if (resolvedPath == null) {
      throw FileNotFoundError(
        'Base SQLite sante_dz_bundled.db introuvable parmi les chemins : $candidatePaths',
      );
    }

    // Ouverture en lecture seule (OpenMode.readOnly) pour sécurité absolue et perf maximale
    _db = sqlite3.open(resolvedPath, mode: OpenMode.readOnly);

    // Optimisations de performance mémoire (Memory-mapped I/O et cache)
    _db!.execute('PRAGMA mmap_size = 268435456;');
    _db!.execute('PRAGMA cache_size = -64000;');
    _db!.execute('PRAGMA temp_store = MEMORY;');

    // Préparation des requêtes fréquentes pour éliminer l'overhead de compilation SQL (< 1 ms)
    _ftsStmt = _db!.prepare('''
      SELECT rowid AS id, nom, categorie, wilaya, commune, telephone, latitude, longitude
      FROM facilities_fts
      WHERE facilities_fts MATCH ?
      LIMIT ?;
    ''');

    _ftsBenchStmt = _db!.prepare('''
      SELECT rowid AS id, nom, categorie, wilaya, commune, telephone, latitude, longitude
      FROM facilities_fts
      WHERE facilities_fts MATCH ?
      LIMIT 20;
    ''');

    _rtreeStmt = _db!.prepare('''
      SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
             f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
      FROM facilities_rtree r
      JOIN facilities f ON f.id = r.id
      WHERE r.min_lat >= ? AND r.max_lat <= ?
        AND r.min_lon >= ? AND r.max_lon <= ?
      LIMIT 100;
    ''');

    _rtreeExtractStmt = _db!.prepare('''
      SELECT id, min_lat, min_lon
      FROM facilities_rtree
      WHERE min_lat >= ? AND max_lat <= ?
        AND min_lon >= ? AND max_lon <= ?
      LIMIT 50;
    ''');

    _isInitialized = true;
  }

  /// Fermeture propre des ressources SQLite
  void dispose() {
    _ftsStmt?.dispose();
    _ftsBenchStmt?.dispose();
    _rtreeStmt?.dispose();
    _rtreeExtractStmt?.dispose();
    _ftsStmt = null;
    _ftsBenchStmt = null;
    _rtreeStmt = null;
    _rtreeExtractStmt = null;
    _db?.dispose();
    _db = null;
    _isInitialized = false;
  }

  Database get db {
    if (!_isInitialized || _db == null) {
      throw StateError('OfflineHealthSearchService non initialisé. Appeler initialize() au préalable.');
    }
    return _db!;
  }

  // ===========================================================================
  // 1. MOTEUR PLEIN TEXTE FTS5 (Recherche sémantique, translittération, accents)
  // ===========================================================================

  /// Normalisation des accents français et translittération arabe/latine
  static String normalizeQuery(String input) {
    var text = input.trim().toLowerCase();

    // Remplacement des voyelles accentuées et cédilles
    const accentMap = {
      'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
      'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
      'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
      'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
      'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
      'ý': 'y', 'ÿ': 'y',
      'ç': 'c', 'ñ': 'n',
    };

    accentMap.forEach((acc, rep) {
      text = text.replaceAll(acc, rep);
    });

    // Équivalences médicales et translittérations algériennes courantes
    final replacements = {
      'docteur': 'dr',
      'hopital': 'hopital',
      'pharmacie': 'pharmacie',
      'laboratoire': 'laboratoire',
      'cabinet': 'cabinet',
      'clinique': 'clinique',
      'chahida': 'chehida',
      'chahid': 'chehid',
      'ben': 'ben',
      'sidi': 'sidi',
      'oued': 'oued',
    };

    replacements.forEach((key, val) {
      text = text.replaceAll(RegExp('\\b$key\\b'), val);
    });

    // Supprimer les caractères de ponctuation SQLite FTS5 dangereux
    text = text.replaceAll(RegExp(r'["\*\^\{\}\[\]\(\)\:\+\-\?]'), ' ');
    return text.trim();
  }

  /// Prépare la clause MATCH FTS5 avec préfixes jokers (*)
  static String formatFtsMatch(String query) {
    final clean = normalizeQuery(query);
    final tokens = clean.split(RegExp(r'\s+')).where((t) => t.isNotEmpty).toList();
    if (tokens.isEmpty) return '*';
    return tokens.map((t) => '$t*').join(' AND ');
  }

  /// Recherche plein texte FTS5 avec tri par pertinence (rank)
  List<HealthFacility> searchFts(String query, {int limit = 50}) {
    if (query.trim().isEmpty) return [];

    final ftsMatch = formatFtsMatch(query);

    final ResultSet results = (_ftsStmt != null)
        ? _ftsStmt!.select([ftsMatch, limit])
        : db.select('''
            SELECT rowid AS id, nom, categorie, wilaya, commune, telephone, latitude, longitude
            FROM facilities_fts
            WHERE facilities_fts MATCH ?
            LIMIT ?;
          ''', [ftsMatch, limit]);

    return results.map((row) => HealthFacility.fromMap(row)).toList();
  }

  // ===========================================================================
  // 2. FILTRAGE SPATIAL R-TREE ("Autour de moi" & Bounding Box)
  // ===========================================================================

  /// Calcul de distance orthodromique (Haversine) en kilomètres
  static double calculateHaversineKm(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const double earthRadiusKm = 6371.0;
    final dLat = _deg2rad(lat2 - lat1);
    final dLon = _deg2rad(lon2 - lon1);

    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_deg2rad(lat1)) *
            math.cos(_deg2rad(lat2)) *
            math.sin(dLon / 2) *
            math.sin(dLon / 2);

    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    return earthRadiusKm * c;
  }

  static double _deg2rad(double deg) => deg * (math.pi / 180.0);

  /// Recherche spatiale par R-Tree pour un rayon géographique donné ("Autour de moi")
  List<HealthFacility> searchAroundMe({
    required double latitude,
    required double longitude,
    double radiusKm = 5.0,
    String? category,
    int limit = 50,
  }) {
    // Calcul de la Bounding Box
    final deltaLat = radiusKm / 111.0;
    final latRad = _deg2rad(latitude);
    final cosLat = math.cos(latRad).abs();
    final deltaLon = radiusKm / (111.0 * (cosLat > 0.05 ? cosLat : 1.0));

    final minLat = latitude - deltaLat;
    final maxLat = latitude + deltaLat;
    final minLon = longitude - deltaLon;
    final maxLon = longitude + deltaLon;

    final ResultSet results;
    if (category == null || category.isEmpty) {
      results = (_rtreeStmt != null)
          ? _rtreeStmt!.select([minLat, maxLat, minLon, maxLon])
          : db.select('''
              SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
                     f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
              FROM facilities_rtree r
              JOIN facilities f ON f.id = r.id
              WHERE r.min_lat >= ? AND r.max_lat <= ?
                AND r.min_lon >= ? AND r.max_lon <= ?
              LIMIT 250;
            ''', [minLat, maxLat, minLon, maxLon]);
    } else {
      results = db.select('''
        SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
               f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
        FROM facilities_rtree r
        JOIN facilities f ON f.id = r.id
        WHERE r.min_lat >= ? AND r.max_lat <= ?
          AND r.min_lon >= ? AND r.max_lon <= ?
          AND f.categorie = ?
        LIMIT 250;
      ''', [minLat, maxLat, minLon, maxLon, category]);
    }

    // Calcul précis en mémoire de la distance Haversine et tri par proximité
    final facilities = <HealthFacility>[];
    for (final row in results) {
      final fac = HealthFacility.fromMap(row);
      final dist = calculateHaversineKm(latitude, longitude, fac.latitude, fac.longitude);
      if (dist <= radiusKm * 1.05) {
        fac.distanceKm = double.parse(dist.toStringAsFixed(2));
        facilities.add(fac);
      }
    }

    facilities.sort((a, b) => (a.distanceKm ?? 0).compareTo(b.distanceKm ?? 0));

    if (facilities.length > limit) {
      return facilities.sublist(0, limit);
    }
    return facilities;
  }

  // ===========================================================================
  // 3. RECHERCHE HYBRIDE COMBINÉE (TEXTE + FACETTES + DISTANCE)
  // ===========================================================================

  /// Recherche multi-critères : FTS5, code wilaya, catégorie, urgence et rayon
  List<HealthFacility> searchHybrid({
    String? query,
    String? wilayaCode,
    String? category,
    bool onlyEmergency = false,
    double? userLat,
    double? userLon,
    double radiusKm = 10.0,
    int limit = 50,
  }) {
    // Vue nationale sans filtre wilaya : charger toutes les fiches (sans contrainte spatiale)
    if ((query == null || query.trim().isEmpty) &&
        (wilayaCode == null || wilayaCode.isEmpty) &&
        (userLat == null || userLon == null)) {
      final sb = StringBuffer();
      sb.writeln('''
        SELECT id, place_id, nom, categorie, wilaya, wilaya_code, commune,
               adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
        FROM facilities
        WHERE 1=1
      ''');
      final params = <dynamic>[];

      if (category != null && category.isNotEmpty) {
        sb.writeln('  AND categorie = ?');
        params.add(category);
      }

      sb.writeln('ORDER BY nom ASC LIMIT ?;');
      params.add(limit > 0 ? limit : 100000); // Pas de limite stricte en vue nationale

      final ResultSet results = db.select(sb.toString(), params);
      var facilities = results.map((r) => HealthFacility.fromMap(r)).toList();

      if (onlyEmergency) {
        facilities = facilities.where((f) => f.isEmergencyOrOnDuty).toList();
      }

      return facilities;
    }

    // Vue nationale avec géolocalisation présente mais sans filtre wilaya/texte : charger tout le pays
    if ((query == null || query.trim().isEmpty) &&
        (wilayaCode == null || wilayaCode.isEmpty)) {
      final sb = StringBuffer();
      sb.writeln('''
        SELECT id, place_id, nom, categorie, wilaya, wilaya_code, commune,
               adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
        FROM facilities
        WHERE 1=1
      ''');
      final params = <dynamic>[];

      if (category != null && category.isNotEmpty) {
        sb.writeln('  AND categorie = ?');
        params.add(category);
      }

      sb.writeln('ORDER BY nom ASC LIMIT ?;');
      params.add(limit > 1000 ? limit : 50000);

      final ResultSet results = db.select(sb.toString(), params);
      var facilities = results.map((r) => HealthFacility.fromMap(r)).toList();

      if (onlyEmergency) {
        facilities = facilities.where((f) => f.isEmergencyOrOnDuty).toList();
      }

      if (userLat != null && userLon != null) {
        for (final fac in facilities) {
          fac.distanceKm = double.parse(
            calculateHaversineKm(userLat, userLon, fac.latitude, fac.longitude).toStringAsFixed(2),
          );
        }
        facilities.sort((a, b) => (a.distanceKm ?? 0).compareTo(b.distanceKm ?? 0));
      }

      return facilities;
    }

    // Si une position utilisateur est fournie sans texte, basculer sur R-Tree
    if ((query == null || query.trim().isEmpty) && userLat != null && userLon != null) {
      var res = searchAroundMe(
        latitude: userLat,
        longitude: userLon,
        radiusKm: radiusKm,
        category: category,
        limit: limit * 2,
      );
      if (onlyEmergency) {
        res = res.where((f) => f.isEmergencyOrOnDuty).toList();
      }
      if (wilayaCode != null && wilayaCode.isNotEmpty) {
        res = res.where((f) => f.wilayaCode == wilayaCode).toList();
      }
      return res.take(limit).toList();
    }

    // Si du texte est fourni, utiliser FTS5
    if (query != null && query.trim().isNotEmpty) {
      final ftsMatch = formatFtsMatch(query);
      final sb = StringBuffer();
      sb.writeln('''
        SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
               f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
        FROM facilities f
        JOIN facilities_fts fts ON f.id = fts.rowid
        WHERE facilities_fts MATCH ?
      ''');

      final params = <dynamic>[ftsMatch];

      if (wilayaCode != null && wilayaCode.isNotEmpty) {
        sb.writeln('  AND f.wilaya_code = ?');
        params.add(wilayaCode);
      }

      if (category != null && category.isNotEmpty) {
        sb.writeln('  AND f.categorie = ?');
        params.add(category);
      }

      sb.writeln('ORDER BY fts.rank LIMIT ?;');
      params.add(limit * 2);

      final ResultSet results = db.select(sb.toString(), params);
      var facilities = results.map((r) => HealthFacility.fromMap(r)).toList();

      if (userLat != null && userLon != null) {
        for (final fac in facilities) {
          fac.distanceKm = double.parse(
            calculateHaversineKm(userLat, userLon, fac.latitude, fac.longitude).toStringAsFixed(2),
          );
        }
        facilities.sort((a, b) => (a.distanceKm ?? 0).compareTo(b.distanceKm ?? 0));
      }

      if (onlyEmergency) {
        facilities = facilities.where((f) => f.isEmergencyOrOnDuty).toList();
      }

      return facilities.take(limit).toList();
    }

    // Requête par défaut sur wilaya et catégorie
    final sb = StringBuffer();
    sb.writeln('''
      SELECT id, place_id, nom, categorie, wilaya, wilaya_code, commune,
             adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
      FROM facilities
      WHERE 1=1
    ''');
    final params = <dynamic>[];

    if (wilayaCode != null && wilayaCode.isNotEmpty) {
      sb.writeln('  AND wilaya_code = ?');
      params.add(wilayaCode);
    }

    if (category != null && category.isNotEmpty) {
      sb.writeln('  AND categorie = ?');
      params.add(category);
    }

    sb.writeln('ORDER BY nom ASC LIMIT ?;');
    params.add(limit);

    final ResultSet results = db.select(sb.toString(), params);
    var facilities = results.map((r) => HealthFacility.fromMap(r)).toList();

    if (onlyEmergency) {
      facilities = facilities.where((f) => f.isEmergencyOrOnDuty).toList();
    }

    return facilities;
  }

  // ===========================================================================
  // 4. CONTRÔLE D'INTÉGRITÉ, COUVERTURE & BENCHMARKS
  // ===========================================================================

  /// Comptage exact des fiches (doit renvoyer 35 832)
  int getTotalFacilitiesCount() {
    final row = db.select('SELECT COUNT(*) AS c FROM facilities;').first;
    return (row['c'] as num).toInt();
  }

  /// Couverture des wilayas (doit renvoyer 58)
  int getWilayasCount() {
    final row = db.select('SELECT COUNT(DISTINCT wilaya_code) AS c FROM facilities;').first;
    return (row['c'] as num).toInt();
  }

  /// Récupération de l'ensemble des 58 codes wilayas
  List<String> getAllWilayaCodes() {
    final rows = db.select('SELECT DISTINCT wilaya_code FROM facilities ORDER BY wilaya_code ASC;');
    return rows.map((r) => r['wilaya_code'] as String).toList();
  }

  /// Répartition des effectifs par catégorie
  Map<String, int> getCountByCategory() {
    final rows = db.select('SELECT categorie, COUNT(*) as c FROM facilities GROUP BY categorie ORDER BY c DESC;');
    final map = <String, int>{};
    for (final r in rows) {
      map[r['categorie'] as String] = (r['c'] as num).toInt();
    }
    return map;
  }

  /// Benchmark FTS5 : calcule la latence moyenne d'exécution sur une liste de requêtes courantes
  double benchmarkFtsLatencyMs(List<String> queries, {int limit = 20}) {
    if (queries.isEmpty) return 0.0;

    // Warmup du cache SQLite
    for (final q in queries.take(5)) {
      final match = formatFtsMatch(q);
      _ftsBenchStmt?.select([match]);
    }

    final stopwatch = Stopwatch()..start();
    for (final q in queries) {
      final match = formatFtsMatch(q);
      if (_ftsBenchStmt != null) {
        _ftsBenchStmt!.select([match]);
      } else {
        db.select('''
          SELECT rowid AS id, nom, categorie, wilaya, commune, telephone, latitude, longitude
          FROM facilities_fts
          WHERE facilities_fts MATCH ?
          LIMIT 20;
        ''', [match]);
      }
    }
    stopwatch.stop();
    return stopwatch.elapsedMicroseconds / (queries.length * 1000.0);
  }

  /// Benchmark R-Tree : calcule la latence moyenne d'extraction spatiale
  double benchmarkRtreeLatencyMs({
    required double latitude,
    required double longitude,
    double radiusKm = 5.0,
    int iterations = 100,
  }) {
    final deltaLat = radiusKm / 111.0;
    final latRad = _deg2rad(latitude);
    final cosLat = math.cos(latRad).abs();
    final deltaLon = radiusKm / (111.0 * (cosLat > 0.05 ? cosLat : 1.0));

    final minLat = latitude - deltaLat;
    final maxLat = latitude + deltaLat;
    final minLon = longitude - deltaLon;
    final maxLon = longitude + deltaLon;

    // Warmup
    _rtreeExtractStmt?.select([minLat, maxLat, minLon, maxLon]);

    final stopwatch = Stopwatch()..start();
    for (var i = 0; i < iterations; i++) {
      if (_rtreeExtractStmt != null) {
        _rtreeExtractStmt!.select([minLat, maxLat, minLon, maxLon]);
      } else {
        db.select('''
          SELECT id, min_lat, min_lon
          FROM facilities_rtree
          WHERE min_lat >= ? AND max_lat <= ?
            AND min_lon >= ? AND max_lon <= ?
          LIMIT 50;
        ''', [minLat, maxLat, minLon, maxLon]);
      }
    }
    stopwatch.stop();
    return stopwatch.elapsedMicroseconds / (iterations * 1000.0);
  }
}
class FileNotFoundError implements Exception {
  final String message;
  FileNotFoundError(this.message);
  @override
  String toString() => 'FileNotFoundError: $message';
}
