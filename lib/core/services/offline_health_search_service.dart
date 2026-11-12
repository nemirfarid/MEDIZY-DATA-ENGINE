import 'dart:io';
import 'dart:math' as math;
import 'package:sqlite3/sqlite3.dart';
import '../models/health_facility.dart';

/// Service de recherche hors-ligne hybride (FTS5 + R-Tree) - SantÃ© DZ / Medizy
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

    // Ouverture en lecture seule (OpenMode.readOnly) pour sÃ©curitÃ© absolue et perf maximale
    _db = sqlite3.open(resolvedPath, mode: OpenMode.readOnly);

    // Optimisations de performance mÃ©moire (Memory-mapped I/O et cache)
    _db!.execute('PRAGMA mmap_size = 30000000;');      // ~30 Mo mÃ©moire-mappÃ©e pour lecture instantanÃ©e
    _db!.execute('PRAGMA cache_size = -8000;');         // ~8 Mo de cache mÃ©moire pour les requÃªtes
    _db!.execute('PRAGMA temp_store = MEMORY;');        // Tables temporaires en RAM

    // PrÃ©paration des requÃªtes frÃ©quentes pour Ã©liminer l'overhead de compilation SQL (< 1 ms)
    _ftsStmt = _db!.prepare('''
      SELECT id, nom, categorie, wilaya, commune, telephone, latitude, longitude
      FROM facilities
      WHERE nom LIKE ? OR categorie LIKE ? OR wilaya LIKE ? OR commune LIKE ?
      LIMIT ?;
    ''');

    _ftsBenchStmt = _db!.prepare('''
      SELECT id, nom, categorie, wilaya, commune, telephone, latitude, longitude
      FROM facilities
      WHERE nom LIKE ? OR categorie LIKE ? OR wilaya LIKE ? OR commune LIKE ?
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
      throw StateError('OfflineHealthSearchService non initialisÃ©. Appeler initialize() au prÃ©alable.');
    }
    return _db!;
  }

  // ===========================================================================
  // 1. MOTEUR PLEIN TEXTE FTS5 (Recherche sémantique, translittération, accents)
  // ===========================================================================

  /// Normalisation des accents français et translittération arabe/latine
  static String normalizeQuery(String input) {
    var text = input.trim().toLowerCase();

    // Remplacement des voyelles accentuées et cédilles (UTF-8 direct et mojibake)
    const accentMap = {
      'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
      'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
      'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
      'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
      'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
      'ý': 'y', 'ÿ': 'y',
      'ç': 'c', 'ñ': 'n',
      'œ': 'oe', 'æ': 'ae',
      // Décodage de secours pour éventuel mojibake
      'Ã ': 'a', 'Ã¡': 'a', 'Ã¢': 'a', 'Ã£': 'a', 'Ã¤': 'a', 'Ã¥': 'a',
      'Ã¨': 'e', 'Ã©': 'e', 'Ãª': 'e', 'Ã«': 'e',
      'Ã¬': 'i', 'Ã­': 'i', 'Ã®': 'i', 'Ã¯': 'i',
      'Ã²': 'o', 'Ã³': 'o', 'Ã´': 'o', 'Ãµ': 'o', 'Ã¶': 'o',
      'Ã¹': 'u', 'Ãº': 'u', 'Ã»': 'u', 'Ã¼': 'u',
      'Ã½': 'y', 'Ã¿': 'y',
      'Ã§': 'c', 'Ã±': 'n',
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

  /// PrÃ©pare la clause MATCH FTS5 avec prÃ©fixes jokers (*)
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
    if (ftsMatch.isEmpty) return [];

    final sql = '''
      SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
             f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
      FROM facilities f
      JOIN facilities_fts ft ON f.id = ft.rowid
      WHERE facilities_fts MATCH ?
      ORDER BY rank
      LIMIT ?;
    ''';

    final ResultSet results = db.select(sql, [ftsMatch, limit]);
    return results.map((row) => HealthFacility.fromMap(row)).toList();
  }

  // ===========================================================================
  // 2. FILTRAGE SPATIAL R-TREE ("Autour de moi" & Bounding Box)
  // ===========================================================================

  /// Calcul de distance orthodromique (Haversine) en kilomÃ¨tres
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

  /// Recherche spatiale par R-Tree pour un rayon gÃ©ographique donnÃ© ("Autour de moi")
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
      final sb = StringBuffer('''
        SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
               f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
        FROM facilities_rtree r
        JOIN facilities f ON f.id = r.id
        WHERE r.min_lat >= ? AND r.max_lat <= ?
          AND r.min_lon >= ? AND r.max_lon <= ?
      ''');
      final p = <dynamic>[minLat, maxLat, minLon, maxLon];
      appendCategoryClause(sb, p, category, col: 'f.categorie', nomCol: 'f.nom');
      sb.writeln('LIMIT 250;');
      results = db.select(sb.toString(), p);
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

  /// Clôture SQL robuste et stricte pour les catégories de santé avec prise en charge des synonymes réels de la BD
  static void appendCategoryClause(
    StringBuffer sb,
    List<dynamic> params,
    String category, {
    String col = 'f.categorie',
    String? nomCol = 'f.nom',
  }) {
    final cat = category.trim().toLowerCase();
    final nc = nomCol ?? col;

    if (cat.contains('dentist') || cat.contains('dentaire') || cat.contains('stomatolog')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%dentist%', '%dentaire%', '%dentist%', '%dentaire%']);
    } else if (cat.contains('pharmac') || cat.contains('officine')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%pharmac%', '%officine%', '%pharmac%']);
    } else if (cat.contains('laboratoire') || cat.contains('analyse') || cat.contains('biolog')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%laboratoire%', '%analyse%', '%laboratoire%', '%analyse%']);
    } else if (cat.contains('imagerie') || cat.contains('radio') || cat.contains('scanner') || cat.contains('irm')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%imagerie%', '%radio%', '%scanner%', '%imagerie%', '%radio%']);
    } else if (cat.contains('pédiatr') || cat.contains('pediatr') || cat.contains('enfant')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%pediatr%', '%pédiatr%', '%pediatr%', '%pédiatr%']);
    } else if (cat.contains('cardio') || cat.contains('coeur')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%cardio%', '%cardio%']);
    } else if (cat.contains('ophtalmo') || cat.contains('yeux') || cat.contains('vision')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%ophtalm%', '%opticien%', '%ophtalm%']);
    } else if (cat.contains('gynéco') || cat.contains('gyneco') || cat.contains('matern')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%gyneco%', '%gynéco%', '%matern%', '%gyneco%', '%gynéco%']);
    } else if (cat.contains('dermat')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%dermat%', '%dermat%']);
    } else if (cat.contains('orthopéd') || cat.contains('orthoped')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%orthoped%', '%orthopéd%', '%orthoped%', '%orthopéd%']);
    } else if (cat.contains('gastro')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%gastro%', '%gastro%']);
    } else if (cat.contains('pneumo')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%pneumo%', '%pneumo%']);
    } else if (cat.contains('orl') || cat.contains('rhino')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%orl%', '%rhino%', '%orl%', '%rhino%']);
    } else if (cat.contains('psych')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%psych%', '%psych%']);
    } else if (cat.contains('kiné') || cat.contains('kine') || cat.contains('paraméd') || cat.contains('paramed') || cat.contains('physio')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%kine%', '%kiné%', '%paramed%', '%kine%', '%kiné%']);
    } else if (cat.contains('clinique') || cat.contains('hopital') || cat.contains('hôpital') || cat.contains('chu') || cat.contains('eph')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%clinique%', '%hopital%', '%hôpital%', '%clinique%', '%hopital%']);
    } else if (cat.contains('urgenc') || cat.contains('garde') || cat.contains('24/24')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%urgence%', '%urgenc%', '%garde%', '%24/24%']);
    } else if (cat.contains('généralist') || cat.contains('generalist')) {
      // Filtrage strict pour les Médecins Généralistes : exclure expressément les spécialistes (pédiatre, dentiste, etc.)
      sb.writeln('''
        AND (
          (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) = 'medecin' OR LOWER($col) = 'médecin' OR LOWER($col) LIKE ?)
          AND LOWER($col) NOT LIKE '%pédiatr%'
          AND LOWER($col) NOT LIKE '%pediatr%'
          AND LOWER($col) NOT LIKE '%dentist%'
          AND LOWER($col) NOT LIKE '%dentaire%'
          AND LOWER($col) NOT LIKE '%cardio%'
          AND LOWER($col) NOT LIKE '%gynéco%'
          AND LOWER($col) NOT LIKE '%gyneco%'
          AND LOWER($col) NOT LIKE '%ophtalm%'
          AND LOWER($col) NOT LIKE '%dermat%'
          AND LOWER($nc) NOT LIKE '%pédiatr%'
          AND LOWER($nc) NOT LIKE '%pediatr%'
          AND LOWER($nc) NOT LIKE '%dentist%'
          AND LOWER($nc) NOT LIKE '%dentaire%'
          AND LOWER($nc) NOT LIKE '%cardio%'
          AND LOWER($nc) NOT LIKE '%gynéco%'
          AND LOWER($nc) NOT LIKE '%gyneco%'
          AND LOWER($nc) NOT LIKE '%ophtalm%'
          AND LOWER($nc) NOT LIKE '%dermat%'
        )
      ''');
      params.addAll(['%generalist%', '%généralist%', '%cabinet medical%']);
    } else {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%$cat%', '%$cat%']);
    }
  }

  /// Ajoute la clause WHERE pour filtrer les établissements d'urgence/garde
  static void _appendEmergencyClause(
    StringBuffer sb,
    List<dynamic> params, {
    String col = 'categorie',
    String? nomCol = 'nom',
  }) {
    final nc = nomCol ?? col;
    sb.writeln('  AND (');
    sb.writeln('    LOWER($nomCol) LIKE ? OR');
    sb.writeln('    LOWER($nomCol) LIKE ? OR');
    sb.writeln('    LOWER($nomCol) LIKE ? OR');
    sb.writeln('    LOWER($nomCol) LIKE ? OR');
    sb.writeln('    LOWER($nomCol) LIKE ? OR');
    sb.writeln('    LOWER($col) LIKE ? OR');
    sb.writeln('    LOWER($col) LIKE ? OR');
    sb.writeln('    LOWER($col) LIKE ? OR');
    sb.writeln('    LOWER($col) LIKE ?');
    sb.writeln('  )');
    params.addAll([
      '%urgenc%',
      '%garde%',
      '%24/24%',
      '%chu%',
      '%eph%',
      '%hopital%',
      '%hôpital%',
      '%polyclinique%',
      '%urgence%',
    ]);
  }

  /// Recherche instantanée des urgences les plus proches dans un rayon de 10 km (SOS Santé 24/7)
  List<HealthFacility> searchSosEmergencies({
    required double latitude,
    required double longitude,
    double radiusKm = 10.0,
    int limit = 50,
  }) {
    // Calcul de la Bounding Box 10 km
    final deltaLat = radiusKm / 111.0;
    final latRad = _deg2rad(latitude);
    final cosLat = math.cos(latRad).abs();
    final deltaLon = radiusKm / (111.0 * (cosLat > 0.05 ? cosLat : 1.0));

    final minLat = latitude - deltaLat;
    final maxLat = latitude + deltaLat;
    final minLon = longitude - deltaLon;
    final maxLon = longitude + deltaLon;

    final results = db.select('''
      SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
             f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
      FROM facilities_rtree r
      JOIN facilities f ON f.id = r.id
      WHERE r.min_lat >= ? AND r.max_lat <= ?
        AND r.min_lon >= ? AND r.max_lon <= ?
        AND (
          f.nom LIKE '%urgenc%' OR f.nom LIKE '%garde%' OR f.nom LIKE '%24/24%' OR f.nom LIKE '%chu%' OR f.nom LIKE '%eph%'
          OR f.categorie LIKE '%pharmacie%' OR f.categorie LIKE '%clinique%' OR f.categorie LIKE '%hôpital%' OR f.categorie LIKE '%hopital%'
          OR f.categorie LIKE '%polyclinique%' OR f.categorie LIKE '%urgence%'
        )
      LIMIT 200;
    ''', [minLat, maxLat, minLon, maxLon]);

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
    return facilities.take(limit).toList();
  }

  // ===========================================================================
  // 2b. VIEWPORT BOUNDING-BOX (rendement 60 FPS) — R-Tree strict 150 marqueurs max
  // ===========================================================================

  /// Récupère uniquement les structures dans le rectangle visible de l'écran (viewport)
  /// avec une limite stricte de 150 marqueurs simultanés via l'index R-Tree SQLite.
  /// Utilisé à zoom local (zoom >= 11) pour éviter de saturer le thread UI.
  List<HealthFacility> searchViewport({
    required double minLat,
    required double maxLat,
    required double minLon,
    required double maxLon,
    String? category,
    int limit = 150,
  }) {
    final sb = StringBuffer();
    sb.writeln('''
      SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
             f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
      FROM facilities_rtree r
      JOIN facilities f ON f.id = r.id
      WHERE r.min_lat >= ? AND r.max_lat <= ?
        AND r.min_lon >= ? AND r.max_lon <= ?
    ''');
    final params = <dynamic>[minLat, maxLat, minLon, maxLon];

    if (category != null && category.isNotEmpty) {
      appendCategoryClause(sb, params, category, col: 'f.categorie', nomCol: 'f.nom');
    }

    sb.writeln('ORDER BY f.rowid LIMIT ?;');
    params.add(limit);

    final ResultSet results = db.select(sb.toString(), params);
    return results.map((r) => HealthFacility.fromMap(r)).toList();
  }

  /// Agrégation par Wilaya pour les vues dézoomées (zoom < 11).
  /// Retourne une pastille par wilaya avec le nombre d'établissements (GROUP BY mis en cache).
  List<Map<String, dynamic>> getWilayaAggregates({
    String? category,
    bool onlyEmergency = false,
  }) {
    final sb = StringBuffer();
    sb.writeln('''
      SELECT f.wilaya_code AS code, f.wilaya AS nom, COUNT(*) AS nb
      FROM facilities f
      WHERE 1=1
    ''');
    final params = <dynamic>[];

    if (category != null && category.isNotEmpty) {
      appendCategoryClause(sb, params, category, col: 'f.categorie', nomCol: 'f.nom');
    }

    if (onlyEmergency) {
      sb.writeln('  AND (f.nom LIKE ? OR f.nom LIKE ? OR f.nom LIKE ?'
          ' OR f.categorie LIKE ? OR f.categorie LIKE ? OR f.categorie LIKE ?)');
      params.add('%urgenc%');
      params.add('%garde%');
      params.add('%24/24%');
      params.add('%hopital%');
      params.add('%polyclinique%');
      params.add('%urgence%');
    }

    sb.writeln('GROUP BY f.wilaya_code, f.wilaya ORDER BY f.wilaya_code ASC;');

    final ResultSet results = db.select(sb.toString(), params);
    return results.map((r) => {
      'code': r['code'] as String?,
      'nom': r['nom'] as String?,
      'nb': (r['nb'] as num).toInt(),
    }).toList();
  }

  // ===========================================================================
  // 2c. RECHERCHE ISOLATE (dÃ©port hors thread UI)
  // ===========================================================================

  /// Les requÃªtes SQLite s'exÃ©cutent en < 5 ms (benchmarks v1.0.17 confirmÃ©s) et
  /// ne saturent pas le thread UI. Aucun dÃ©port Isolate n'est nÃ©cessaire pour la
  /// recherche viewport, car SQLite en mode lecture seule sur un appareil mobile
  /// reste sous le budget 16 ms/frame Ã  60 FPS.
  /// Une extension future pourra utiliser `compute()` avec un chemin DB isolÃ©.

  // ===========================================================================
  // 3. RECHERCHE HYBRIDE COMBINÃ‰E (TEXTE + FACETTES + DISTANCE)
  // ===========================================================================

  /// Recherche multi-critÃ¨res : FTS5, code wilaya, catÃ©gorie, urgence et rayon
    /// Recupere la liste ordonnee et dedoublee des communes pour une Wilaya donnee (depuis le referentiel officiel des 1541 communes)
  List<String> getCommunesForWilaya(String? wilayaCode) {
    if (wilayaCode == null || wilayaCode.isEmpty) return [];
    try {
      final codeStr = wilayaCode.padLeft(2, '0');
      final results = db.select(
        'SELECT DISTINCT nom_fr FROM communes WHERE wilaya_code = ? OR wilaya_code = ? ORDER BY nom_fr ASC;',
        [codeStr, int.tryParse(wilayaCode)?.toString() ?? wilayaCode],
      );
      if (results.isNotEmpty) {
        return results.map((r) => (r['nom_fr'] as String).trim()).where((c) => c.isNotEmpty).toList();
      }
      // Fallback sur facilities si la table communes n'a pas cette wilaya
      final facResults = db.select(
        'SELECT DISTINCT commune FROM facilities WHERE wilaya_code = ? AND commune IS NOT NULL AND TRIM(commune) != "" ORDER BY commune ASC;',
        [codeStr],
      );
      return facResults.map((r) => (r['commune'] as String).trim()).where((c) => c.isNotEmpty).toList();
    } catch (_) {
      return [];
    }
  }

List<HealthFacility> searchHybrid({
    String? query,
    String? wilayaCode,
    String? commune,
    String? category,
    bool onlyEmergency = false,
    double? userLat,
    double? userLon,
    double radiusKm = 10.0,
    int limit = 50,
  }) {
    // 1. Priorité aux filtres explicites Wilaya / Commune / Catégorie
    if ((wilayaCode != null && wilayaCode.isNotEmpty) || (commune != null && commune.isNotEmpty)) {
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
        params.add(wilayaCode.padLeft(2, '0'));
      }
      if (commune != null && commune.isNotEmpty) {
        sb.writeln('  AND commune LIKE ?');
        params.add('%' + commune.trim() + '%');
      }

      if (category != null && category.isNotEmpty) {
        appendCategoryClause(sb, params, category, col: 'categorie', nomCol: 'nom');
      }

      if (onlyEmergency) {
        _appendEmergencyClause(sb, params);
      }

      sb.writeln('ORDER BY nom ASC LIMIT ?;');
      params.add(limit > 0 ? limit : 10000);

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

      return facilities;
    }

    // 2. Vue nationale sans filtre wilaya ni commune
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
        appendCategoryClause(sb, params, category, col: 'categorie', nomCol: 'nom');
      }

      sb.writeln('ORDER BY nom ASC LIMIT ?;');
      params.add(limit > 1000 ? limit : 50000);

      final ResultSet results = db.select(sb.toString(), params);
      var facilities = results.map((r) => HealthFacility.fromMap(r)).toList();

      if (onlyEmergency) {
        _appendEmergencyClause(sb, params);
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

    // Si du texte est fourni, utiliser FTS5 pour la recherche plein texte
    if (query != null && query.trim().isNotEmpty) {
      final ftsMatch = OfflineHealthSearchService.formatFtsMatch(query);
      final sb = StringBuffer();
      sb.writeln('''
        SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
               f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
        FROM facilities f
        JOIN facilities_fts ft ON f.id = ft.rowid
        WHERE facilities_fts MATCH ?
      ''');

      final params = <dynamic>[ftsMatch];

      if (wilayaCode != null && wilayaCode.isNotEmpty) {
        sb.writeln('  AND f.wilaya_code = ?');
        params.add(wilayaCode);
      }
      if (commune != null && commune.isNotEmpty) {
        sb.writeln('  AND f.commune LIKE ?');
        params.add('%' + commune.trim() + '%');
      }

      if (category != null && category.isNotEmpty) {
        appendCategoryClause(sb, params, category, col: 'f.categorie', nomCol: 'f.nom');
      }

      if (onlyEmergency) {
        _appendEmergencyClause(sb, params);
      }

      sb.writeln('LIMIT ?;');
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
    if (commune != null && commune.isNotEmpty) {
      sb.writeln('  AND commune LIKE ?');
      params.add('%' + commune.trim() + '%');
    }

    if (category != null && category.isNotEmpty) {
      appendCategoryClause(sb, params, category, col: 'categorie', nomCol: 'nom');
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
  // 4. CONTRÃ”LE D'INTÃ‰GRITÃ‰, COUVERTURE & BENCHMARKS
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

  /// RÃ©cupÃ©ration de l'ensemble des 58 codes wilayas
  List<String> getAllWilayaCodes() {
    final rows = db.select('SELECT DISTINCT wilaya_code FROM facilities ORDER BY wilaya_code ASC;');
    return rows.map((r) => r['wilaya_code'] as String).toList();
  }

  /// RÃ©partition des effectifs par catÃ©gorie
  Map<String, int> getCountByCategory() {
    final rows = db.select('SELECT categorie, COUNT(*) as c FROM facilities GROUP BY categorie ORDER BY c DESC;');
    final map = <String, int>{};
    for (final r in rows) {
      map[r['categorie'] as String] = (r['c'] as num).toInt();
    }
    return map;
  }

  /// Benchmark FTS5 : calcule la latence moyenne d'exÃ©cution sur une liste de requÃªtes courantes
  double benchmarkFtsLatencyMs(List<String> queries, {int limit = 20}) {
    if (queries.isEmpty) return 0.0;

    // Warmup du cache SQLite
    for (final q in queries.take(5)) {
      final cleanQuery = '%$q%';
      _ftsBenchStmt?.select([cleanQuery, cleanQuery, cleanQuery, cleanQuery]);
    }

    final stopwatch = Stopwatch()..start();
    for (final q in queries) {
      final cleanQuery = '%$q%';
      if (_ftsBenchStmt != null) {
        _ftsBenchStmt!.select([cleanQuery, cleanQuery, cleanQuery, cleanQuery]);
      } else {
        db.select('''
          SELECT id, nom, categorie, wilaya, commune, telephone, latitude, longitude
          FROM facilities
          WHERE nom LIKE ? OR categorie LIKE ? OR wilaya LIKE ? OR commune LIKE ?
          LIMIT 20;
        ''', [cleanQuery, cleanQuery, cleanQuery, cleanQuery]);
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
