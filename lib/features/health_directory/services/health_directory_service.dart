import 'package:sqlite3/sqlite3.dart';
import '../../../core/errors/database_failure.dart';
import '../../../core/models/geo_models.dart';
import '../../../core/models/health_professional.dart';
import '../../../core/models/health_search_filter.dart';
import '../../../core/models/pharmacy.dart';
import '../../../core/result/result.dart';
import '../../../core/services/sqlite_database_manager.dart';

/// Contrat du service de consultation de l'annuaire national de santé
abstract interface class IHealthDirectoryService {
  Future<Result<void, DatabaseFailure>> initialize({String? customPath});
  Future<Result<List<HealthProfessional>, DatabaseFailure>> search(HealthSearchFilter filter);
  Future<Result<List<HealthProfessional>, DatabaseFailure>> searchViewport({
    required double minLat,
    required double maxLat,
    required double minLon,
    required double maxLon,
    String? category,
    int limit = 150,
  });
  Future<Result<List<Wilaya>, DatabaseFailure>> getWilayas();
  Future<Result<List<Commune>, DatabaseFailure>> getCommunesForWilaya(String wilayaCode);
  Future<Result<List<String>, DatabaseFailure>> getSpecialties();
  void dispose();
}

/// Implémentation Offline-First du service d'annuaire de santé
class HealthDirectoryService implements IHealthDirectoryService {
  final SqliteDatabaseManager _dbManager;

  HealthDirectoryService({SqliteDatabaseManager? dbManager})
      : _dbManager = dbManager ?? SqliteDatabaseManager();

  @override
  Future<Result<void, DatabaseFailure>> initialize({String? customPath}) async {
    return _dbManager.initialize(customPath: customPath);
  }

  /// Prépare la syntaxe MATCH FTS5 avec préfixes jokers (*)
  static String formatFtsQuery(String query) {
    var text = query.trim().toLowerCase();
    const accentMap = {
      'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a',
      'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
      'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
      'ò': 'o', 'ó': 'o', 'ô': 'o', 'ö': 'o',
      'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
      'ç': 'c',
    };
    accentMap.forEach((acc, rep) {
      text = text.replaceAll(acc, rep);
    });
    text = text.replaceAll(RegExp(r'["\*\^\{\}\[\]\(\)\:\+\-\?]'), ' ').trim();
    final tokens = text.split(RegExp(r'\s+')).where((t) => t.isNotEmpty).toList();
    if (tokens.isEmpty) return '';
    return tokens.map((t) => '$t*').join(' AND ');
  }

  @override
  Future<Result<List<HealthProfessional>, DatabaseFailure>> search(
    HealthSearchFilter filter,
  ) async {
    final dbResult = _dbManager.getDatabase();
    if (dbResult.isFailure) {
      return Failure(dbResult.errorOrNull!);
    }
    final db = dbResult.dataOrNull!;

    try {
      final whereClauses = <String>[];
      final params = <Object?>[];
      String fromSql = 'facilities f';

      final queryText = filter.query?.trim();
      final hasFtsQuery = queryText != null && queryText.isNotEmpty;
      final ftsMatch = hasFtsQuery ? formatFtsQuery(queryText) : '';

      if (hasFtsQuery && ftsMatch.isNotEmpty) {
        final cleanQuery = '%$queryText%';
        whereClauses.add('(f.nom LIKE ? OR f.commune LIKE ? OR f.adresse LIKE ? OR f.wilaya LIKE ?)');
        params.addAll([cleanQuery, cleanQuery, cleanQuery, cleanQuery]);
      } else if (hasFtsQuery) {
        final cleanQuery = '%$queryText%';
        whereClauses.add('(f.nom LIKE ? OR f.commune LIKE ? OR f.adresse LIKE ?)');
        params.addAll([cleanQuery, cleanQuery, cleanQuery]);
      }

      if (filter.wilayaCode != null && filter.wilayaCode!.trim().isNotEmpty) {
        final code = filter.wilayaCode!.trim().padLeft(2, '0');
        whereClauses.add('f.wilaya_code = ?');
        params.add(code);
      }

      if (filter.commune != null && filter.commune!.trim().isNotEmpty) {
        whereClauses.add('LOWER(f.commune) = LOWER(?)');
        params.add(filter.commune!.trim());
      }

      if (filter.specialty != null && filter.specialty!.trim().isNotEmpty) {
        _appendCategoryClause(whereClauses, params, filter.specialty!, col: 'f.categorie', nomCol: 'f.nom');
      }

      final whereSql = whereClauses.isEmpty ? '' : 'WHERE ${whereClauses.join(' AND ')}';
      final sql = '''
        SELECT f.id, f.place_id, f.nom, f.categorie, f.wilaya, f.wilaya_code, f.commune,
               f.adresse, f.telephone, f.site_web, f.note, f.nombre_avis, f.latitude, f.longitude, f.source
        FROM $fromSql
        $whereSql
        ORDER BY f.nom ASC
        LIMIT ? OFFSET ?;
      ''';

      params.add(filter.limit);
      params.add(filter.offset);

      ResultSet resultSet;
      try {
        resultSet = db.select(sql, params);
      } catch (_) {
        // En cas d'erreur de syntaxe FTS, repli défensif sur LIKE
        if (hasFtsQuery) {
          final fallbackWhere = <String>[];
          final fallbackParams = <Object?>[];
          final cleanQuery = '%$queryText%';
          fallbackWhere.add('(nom LIKE ? OR commune LIKE ? OR adresse LIKE ?)');
          fallbackParams.addAll([cleanQuery, cleanQuery, cleanQuery]);

          if (filter.wilayaCode != null && filter.wilayaCode!.trim().isNotEmpty) {
            fallbackWhere.add('wilaya_code = ?');
            fallbackParams.add(filter.wilayaCode!.trim().padLeft(2, '0'));
          }
          if (filter.commune != null && filter.commune!.trim().isNotEmpty) {
            fallbackWhere.add('LOWER(commune) = LOWER(?)');
            fallbackParams.add(filter.commune!.trim());
          }
          if (filter.specialty != null && filter.specialty!.trim().isNotEmpty) {
            _appendCategoryClause(fallbackWhere, fallbackParams, filter.specialty!, col: 'categorie', nomCol: 'nom');
          }
          final fallbackSql = '''
            SELECT id, place_id, nom, categorie, wilaya, wilaya_code, commune,
                   adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
            FROM facilities
            WHERE ${fallbackWhere.join(' AND ')}
            ORDER BY nom ASC
            LIMIT ? OFFSET ?;
          ''';
          fallbackParams.add(filter.limit);
          fallbackParams.add(filter.offset);
          resultSet = db.select(fallbackSql, fallbackParams);
        } else {
          rethrow;
        }
      }

      final results = <HealthProfessional>[];

      for (final Row row in resultSet) {
        final map = <String, Object?>{
          'id': row['id'],
          'place_id': row['place_id'],
          'nom': row['nom'],
          'categorie': row['categorie'],
          'wilaya': row['wilaya'],
          'wilaya_code': row['wilaya_code'],
          'commune': row['commune'],
          'adresse': row['adresse'],
          'telephone': row['telephone'],
          'site_web': row['site_web'],
          'note': row['note'],
          'nombre_avis': row['nombre_avis'],
          'latitude': row['latitude'],
          'longitude': row['longitude'],
          'source': row['source'],
        };

        final cat = (row['categorie'] as String?)?.toLowerCase() ?? '';
        if (cat.contains('pharmacie')) {
          results.add(Pharmacy.fromRow(map));
        } else {
          results.add(HealthProfessional.fromRow(map));
        }
      }

      return Success(List.unmodifiable(results));
    } catch (e, stack) {
      return Failure(
        DatabaseExecutionFailure('Échec lors de l\'exécution de la recherche: $e', stack),
      );
    }
  }

  @override
  Future<Result<List<HealthProfessional>, DatabaseFailure>> searchViewport({
    required double minLat,
    required double maxLat,
    required double minLon,
    required double maxLon,
    String? category,
    int limit = 150,
  }) async {
    final dbResult = _dbManager.getDatabase();
    if (dbResult.isFailure) {
      return Failure(dbResult.errorOrNull!);
    }
    final db = dbResult.dataOrNull!;

    try {
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

      if (category != null && category.trim().isNotEmpty) {
        final dummyList = <String>[];
        _appendCategoryClause(dummyList, params, category.trim(), col: 'f.categorie', nomCol: 'f.nom');
        for (final clause in dummyList) {
          sb.writeln('  AND $clause');
        }
      }

      sb.writeln('ORDER BY f.nom ASC LIMIT ?;');
      params.add(limit);

      final ResultSet resultSet = db.select(sb.toString(), params);
      final results = <HealthProfessional>[];

      for (final Row row in resultSet) {
        final map = <String, Object?>{
          'id': row['id'],
          'place_id': row['place_id'],
          'nom': row['nom'],
          'categorie': row['categorie'],
          'wilaya': row['wilaya'],
          'wilaya_code': row['wilaya_code'],
          'commune': row['commune'],
          'adresse': row['adresse'],
          'telephone': row['telephone'],
          'site_web': row['site_web'],
          'note': row['note'],
          'nombre_avis': row['nombre_avis'],
          'latitude': row['latitude'],
          'longitude': row['longitude'],
          'source': row['source'],
        };

        final cat = (row['categorie'] as String?)?.toLowerCase() ?? '';
        if (cat.contains('pharmacie')) {
          results.add(Pharmacy.fromRow(map));
        } else {
          results.add(HealthProfessional.fromRow(map));
        }
      }

      return Success(List.unmodifiable(results));
    } catch (e, stack) {
      return Failure(
        DatabaseExecutionFailure('Échec lors de la recherche spatiale viewport: $e', stack),
      );
    }
  }

  @override
  Future<Result<List<Wilaya>, DatabaseFailure>> getWilayas() async {
    final dbResult = _dbManager.getDatabase();
    if (dbResult.isFailure) {
      return Failure(dbResult.errorOrNull!);
    }
    final db = dbResult.dataOrNull!;

    try {
      const sql = '''
        SELECT wilaya_code, MIN(wilaya) as wilaya, COUNT(*) as total_facilities
        FROM facilities
        WHERE wilaya_code IS NOT NULL AND wilaya_code != ''
        GROUP BY wilaya_code
        ORDER BY CAST(wilaya_code AS INTEGER) ASC;
      ''';

      final ResultSet resultSet = db.select(sql);
      final wilayas = resultSet.map((row) {
        return Wilaya.fromMap({
          'wilaya_code': row['wilaya_code'],
          'wilaya': row['wilaya'],
          'total_facilities': row['total_facilities'],
        });
      }).toList();

      return Success(List.unmodifiable(wilayas));
    } catch (e, stack) {
      return Failure(
        DatabaseExecutionFailure('Échec lors de la récupération des wilayas: $e', stack),
      );
    }
  }

  @override
  Future<Result<List<Commune>, DatabaseFailure>> getCommunesForWilaya(
    String wilayaCode,
  ) async {
    final dbResult = _dbManager.getDatabase();
    if (dbResult.isFailure) {
      return Failure(dbResult.errorOrNull!);
    }
    final db = dbResult.dataOrNull!;

    try {
      final code = wilayaCode.trim().padLeft(2, '0');
      const sql = '''
        SELECT commune, wilaya_code, COUNT(*) as total_facilities
        FROM facilities
        WHERE wilaya_code = ? AND commune IS NOT NULL AND commune != ''
        GROUP BY commune
        ORDER BY commune ASC;
      ''';

      final ResultSet resultSet = db.select(sql, [code]);
      final communes = resultSet.map((row) {
        return Commune.fromMap({
          'commune': row['commune'],
          'wilaya_code': row['wilaya_code'],
          'total_facilities': row['total_facilities'],
        });
      }).toList();

      return Success(List.unmodifiable(communes));
    } catch (e, stack) {
      return Failure(
        DatabaseExecutionFailure(
          'Échec lors de la récupération des communes pour la wilaya $wilayaCode: $e',
          stack,
        ),
      );
    }
  }

  @override
  Future<Result<List<String>, DatabaseFailure>> getSpecialties() async {
    final dbResult = _dbManager.getDatabase();
    if (dbResult.isFailure) {
      return Failure(dbResult.errorOrNull!);
    }
    final db = dbResult.dataOrNull!;

    try {
      const sql = '''
        SELECT categorie, COUNT(*) as count
        FROM facilities
        WHERE categorie IS NOT NULL AND categorie != ''
        GROUP BY categorie
        ORDER BY count DESC, categorie ASC;
      ''';

      final ResultSet resultSet = db.select(sql);
      final specialties = resultSet
          .map((row) => (row['categorie'] as String?)?.trim() ?? '')
          .where((s) => s.isNotEmpty)
          .toList();

      return Success(List.unmodifiable(specialties));
    } catch (e, stack) {
      return Failure(
        DatabaseExecutionFailure(
          'Échec lors de la récupération des catégories: $e',
          stack,
        ),
      );
    }
  }

  static void _appendCategoryClause(
    List<String> whereClauses,
    List<dynamic> params,
    String category, {
    String col = 'f.categorie',
    String? nomCol = 'f.nom',
  }) {
    final cat = category.trim().toLowerCase();
    switch (cat) {
      case 'dentiste':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
        params.addAll(['dentiste', '%dentist%', '%dentaire%']);
        break;
      case 'pharmacie':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
        params.addAll(['pharmacie', '%pharmacie%', '%officine%']);
        break;
      case 'laboratoire':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
        params.addAll(['laboratoire', '%laboratoire%', '%analyse%']);
        break;
      case 'imagerie':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
        params.addAll(['imagerie', '%imagerie%', '%radiolog%', '%scanner%']);
        break;
      case 'pédiatre':
      case 'pediatre':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
        params.addAll(['pédiatre', '%pédiat%', '%pediat%']);
        break;
      case 'cardiologue':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ?)');
        params.addAll(['cardiologue', '%cardio%']);
        break;
      case 'généraliste':
      case 'generaliste':
        whereClauses.add('''
          (
            (LOWER($col) = 'généraliste' OR LOWER($col) LIKE '%généralist%' OR LOWER($col) LIKE '%generalist%' OR LOWER($col) = 'medecin' OR LOWER($col) = 'médecin')
            AND LOWER($col) NOT LIKE '%pédiatr%'
            AND LOWER($col) NOT LIKE '%dentist%'
            AND LOWER($col) NOT LIKE '%cardio%'
            AND LOWER($col) NOT LIKE '%gynéco%'
            AND LOWER($col) NOT LIKE '%ophtalm%'
          )
        ''');
        break;
      case 'clinique':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
        params.addAll(['clinique', '%clinique%', '%hôpital%', '%hopital%']);
        break;
      case 'gynécologue':
      case 'gynecologue':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
        params.addAll(['gynécologue', '%gynéco%', '%gyneco%']);
        break;
      case 'ophtalmologue':
      case 'ophtalmo':
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ?)');
        params.addAll(['ophtalmologue', '%ophtalmo%']);
        break;
      case 'urgences':
      case 'urgence':
        if (nomCol != null) {
          whereClauses.add('(LOWER($col) LIKE ? OR LOWER($nomCol) LIKE ? OR LOWER($nomCol) LIKE ? OR LOWER($nomCol) LIKE ?)');
          params.addAll(['%urgence%', '%urgenc%', '%garde%', '%24/24%']);
        } else {
          whereClauses.add('(LOWER($col) LIKE ? OR LOWER($col) LIKE ?)');
          params.addAll(['%urgence%', '%hopital%']);
        }
        break;
      default:
        whereClauses.add('(LOWER($col) = ? OR LOWER($col) LIKE ?)');
        params.addAll([cat, '%$cat%']);
        break;
    }
  }

  @override
  void dispose() {
    _dbManager.dispose();
  }
}
