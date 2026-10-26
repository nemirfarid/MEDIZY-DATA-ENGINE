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

      if (filter.wilayaCode != null && filter.wilayaCode!.trim().isNotEmpty) {
        final code = filter.wilayaCode!.trim().padLeft(2, '0');
        whereClauses.add('wilaya_code = ?');
        params.add(code);
      }

      if (filter.commune != null && filter.commune!.trim().isNotEmpty) {
        whereClauses.add('LOWER(commune) = LOWER(?)');
        params.add(filter.commune!.trim());
      }

      if (filter.specialty != null && filter.specialty!.trim().isNotEmpty) {
        whereClauses.add('LOWER(categorie) = LOWER(?)');
        params.add(filter.specialty!.trim());
      }

      if (filter.query != null && filter.query!.trim().isNotEmpty) {
        final cleanQuery = '%${filter.query!.trim()}%';
        whereClauses.add('(nom LIKE ? OR commune LIKE ? OR adresse LIKE ?)');
        params.addAll([cleanQuery, cleanQuery, cleanQuery]);
      }

      final whereSql = whereClauses.isEmpty ? '' : 'WHERE ${whereClauses.join(' AND ')}';
      final sql = '''
        SELECT id, place_id, nom, categorie, wilaya, wilaya_code, commune,
               adresse, telephone, site_web, note, nombre_avis, latitude, longitude, source
        FROM facilities
        $whereSql
        ORDER BY nom ASC
        LIMIT ? OFFSET ?;
      ''';

      params.add(filter.limit);
      params.add(filter.offset);

      final ResultSet resultSet = db.select(sql, params);
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

  @override
  void dispose() {
    _dbManager.dispose();
  }
}
