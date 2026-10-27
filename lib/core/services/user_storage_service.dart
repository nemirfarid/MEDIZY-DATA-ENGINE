import 'dart:convert';
import 'package:sqlite3/sqlite3.dart';
import '../errors/database_failure.dart';
import '../models/crowd_report.dart';
import '../models/health_professional.dart';
import '../models/pharmacy.dart';
import '../result/result.dart';

/// Contrat d'accès au stockage local persistant de l'utilisateur (Favoris, Historique, Signalements, Patches)
abstract interface class IUserStorageService {
  Future<Result<void, DatabaseFailure>> initialize({String? customPath});

  // Favoris
  Future<Result<bool, DatabaseFailure>> toggleFavorite(HealthProfessional facility);
  Future<Result<bool, DatabaseFailure>> isFavorite(int facilityId);
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getFavorites();
  Future<Result<void, DatabaseFailure>> savePersonalNote(int facilityId, String note);
  Future<Result<String?, DatabaseFailure>> getPersonalNote(int facilityId);

  // Historique des consultations (plafonné à 20)
  Future<Result<void, DatabaseFailure>> recordView(HealthProfessional facility);
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getRecentViews({int limit = 20});

  // Signalements en file d'attente
  Future<Result<CrowdReport, DatabaseFailure>> enqueueReport(CrowdReport report);
  Future<Result<List<CrowdReport>, DatabaseFailure>> getPendingReports();
  Future<Result<void, DatabaseFailure>> markReportAsSynced(int reportId);
  Future<Result<void, DatabaseFailure>> markReportsAsSyncedBatch(List<int> reportIds, DateTime syncedAt);
  Future<Result<void, DatabaseFailure>> incrementReportsRetryCount(List<int> reportIds);

  // Mises à jour différentielles (DeltaPatches) & Audit
  Future<Result<String?, DatabaseFailure>> getMetadata(String key);
  Future<Result<void, DatabaseFailure>> setMetadata(String key, String value);
  Future<Result<void, DatabaseFailure>> applyFacilityPatch({
    required String patchId,
    required int version,
    required List<HealthProfessional> upserts,
    required List<int> deletions,
  });
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getPatchedFacilities();

  void dispose();
}

/// Implémentation SQLite de la base de données utilisateur dédiée (Offline-First)
class UserStorageService implements IUserStorageService {
  static final UserStorageService instance = UserStorageService();

  UserStorageService();

  factory UserStorageService.inMemory() {
    final svc = UserStorageService();
    svc.initialize(customPath: ':memory:');
    return svc;
  }

  Database? _db;
  bool _isInitialized = false;

  bool get isInitialized => _isInitialized && _db != null;

  @override
  Future<Result<void, DatabaseFailure>> initialize({String? customPath}) async {
    if (_isInitialized && _db != null) {
      return const Success(null);
    }

    try {
      final dbPath = customPath ?? 'sante_dz_user_data.db';
      final db = sqlite3.open(dbPath);

      // 1. Table des favoris avec note personnelle
      db.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
          facility_id INTEGER PRIMARY KEY,
          facility_json TEXT NOT NULL,
          personal_note TEXT,
          created_at INTEGER NOT NULL
        );
      ''');

      try {
        db.execute('ALTER TABLE user_favorites ADD COLUMN personal_note TEXT;');
      } catch (_) {}

      // 2. Table de l'historique de consultation
      db.execute('''
        CREATE TABLE IF NOT EXISTS user_history (
          facility_id INTEGER PRIMARY KEY,
          facility_json TEXT NOT NULL,
          viewed_at INTEGER NOT NULL
        );
      ''');

      // 3. File d'attente des signalements collaboratifs avec gestion du retry et horodatage de sync
      db.execute('''
        CREATE TABLE IF NOT EXISTS pending_reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          facility_id INTEGER NOT NULL,
          facility_name TEXT NOT NULL,
          report_type TEXT NOT NULL,
          description TEXT,
          suggested_phone TEXT,
          suggested_address TEXT,
          created_at TEXT NOT NULL,
          retry_count INTEGER NOT NULL DEFAULT 0,
          synced_at TEXT,
          is_synced INTEGER NOT NULL DEFAULT 0
        );
      ''');

      // 4. Métadonnées d'audit et versions
      db.execute('''
        CREATE TABLE IF NOT EXISTS sync_metadata (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at INTEGER NOT NULL
        );
      ''');

      // 5. Table de surcouche des patchs différentiels incrémentaux
      db.execute('''
        CREATE TABLE IF NOT EXISTS facility_patches (
          facility_id INTEGER PRIMARY KEY,
          patch_id TEXT NOT NULL,
          version INTEGER NOT NULL,
          facility_json TEXT NOT NULL,
          is_deleted INTEGER NOT NULL DEFAULT 0,
          applied_at INTEGER NOT NULL
        );
      ''');

      _db = db;
      _isInitialized = true;
      return const Success(null);
    } catch (e, stack) {
      return Failure(
        DatabaseExecutionFailure('Échec lors de l\'initialisation de la base utilisateur: $e', stack),
      );
    }
  }

  @override
  Future<Result<bool, DatabaseFailure>> toggleFavorite(HealthProfessional facility) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final check = db.select('SELECT facility_id FROM user_favorites WHERE facility_id = ?;', [facility.id]);

      if (check.isNotEmpty) {
        db.execute('DELETE FROM user_favorites WHERE facility_id = ?;', [facility.id]);
        return const Success(false);
      } else {
        final jsonStr = jsonEncode(facility.toMap());
        final now = DateTime.now().millisecondsSinceEpoch;
        db.execute(
          'INSERT INTO user_favorites (facility_id, facility_json, created_at) VALUES (?, ?, ?);',
          [facility.id, jsonStr, now],
        );
        return const Success(true);
      }
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec du basculement du favori: $e', stack));
    }
  }

  @override
  Future<Result<bool, DatabaseFailure>> isFavorite(int facilityId) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final check = db.select('SELECT facility_id FROM user_favorites WHERE facility_id = ?;', [facilityId]);
      return Success(check.isNotEmpty);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de vérification du favori: $e', stack));
    }
  }

  @override
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getFavorites() async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final rows = db.select('SELECT facility_json FROM user_favorites ORDER BY created_at DESC;');
      final list = <HealthProfessional>[];

      for (final row in rows) {
        final jsonStr = row['facility_json'] as String;
        final map = jsonDecode(jsonStr) as Map<String, dynamic>;
        final cat = (map['categorie'] as String?)?.toLowerCase() ?? '';
        if (cat.contains('pharmacie')) {
          list.add(Pharmacy.fromRow(map));
        } else {
          list.add(HealthProfessional.fromRow(map));
        }
      }

      return Success(List.unmodifiable(list));
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de récupération des favoris: $e', stack));
    }
  }

  @override
  Future<Result<void, DatabaseFailure>> savePersonalNote(int facilityId, String note) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      db.execute('''
        INSERT INTO user_favorites (facility_id, facility_json, personal_note, created_at)
        VALUES (?, '{}', ?, ?)
        ON CONFLICT(facility_id) DO UPDATE SET personal_note = excluded.personal_note;
      ''', [facilityId, note.trim(), DateTime.now().millisecondsSinceEpoch]);
      return const Success(null);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Erreur enregistrement note: $e', stack));
    }
  }

  @override
  Future<Result<String?, DatabaseFailure>> getPersonalNote(int facilityId) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final rows = db.select(
        'SELECT personal_note FROM user_favorites WHERE facility_id = ?;',
        [facilityId],
      );
      if (rows.isEmpty) return const Success(null);
      return Success(rows.first['personal_note'] as String?);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Erreur lecture note: $e', stack));
    }
  }

  @override
  Future<Result<void, DatabaseFailure>> recordView(HealthProfessional facility) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final jsonStr = jsonEncode(facility.toMap());
      final now = DateTime.now().millisecondsSinceEpoch;

      db.execute(
        'INSERT OR REPLACE INTO user_history (facility_id, facility_json, viewed_at) VALUES (?, ?, ?);',
        [facility.id, jsonStr, now],
      );

      // Plafonnement strict aux 20 dernières fiches consultées
      db.execute('''
        DELETE FROM user_history
        WHERE facility_id NOT IN (
          SELECT facility_id FROM user_history ORDER BY viewed_at DESC LIMIT 20
        );
      ''');

      return const Success(null);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec d\'enregistrement dans l\'historique: $e', stack));
    }
  }

  @override
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getRecentViews({int limit = 20}) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final rows = db.select(
        'SELECT facility_json FROM user_history ORDER BY viewed_at DESC LIMIT ?;',
        [limit],
      );
      final list = <HealthProfessional>[];

      for (final row in rows) {
        final jsonStr = row['facility_json'] as String;
        final map = jsonDecode(jsonStr) as Map<String, dynamic>;
        final cat = (map['categorie'] as String?)?.toLowerCase() ?? '';
        if (cat.contains('pharmacie')) {
          list.add(Pharmacy.fromRow(map));
        } else {
          list.add(HealthProfessional.fromRow(map));
        }
      }

      return Success(List.unmodifiable(list));
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de récupération de l\'historique: $e', stack));
    }
  }

  @override
  Future<Result<CrowdReport, DatabaseFailure>> enqueueReport(CrowdReport report) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      db.execute(
        '''
        INSERT INTO pending_reports (
          facility_id, facility_name, report_type, description, suggested_phone, suggested_address, created_at, retry_count, is_synced
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?);
        ''',
        [
          report.facilityId,
          report.facilityName,
          report.reportType.name,
          report.description,
          report.suggestedPhone,
          report.suggestedAddress,
          report.createdAt.toIso8601String(),
          report.isSynced ? 1 : 0,
        ],
      );

      final insertedId = db.lastInsertRowId;
      return Success(report.copyWith(id: insertedId));
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec d\'enregistrement du signalement: $e', stack));
    }
  }

  @override
  Future<Result<List<CrowdReport>, DatabaseFailure>> getPendingReports() async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final rows = db.select(
        'SELECT id, facility_id, facility_name, report_type, description, suggested_phone, suggested_address, created_at, retry_count, synced_at, is_synced FROM pending_reports WHERE is_synced = 0 ORDER BY id ASC;',
      );
      final reports = rows.map((r) => CrowdReport.fromRow(r)).toList();
      return Success(List.unmodifiable(reports));
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de récupération des signalements: $e', stack));
    }
  }

  @override
  Future<Result<void, DatabaseFailure>> markReportAsSynced(int reportId) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final now = DateTime.now().toUtc().toIso8601String();
      db.execute('UPDATE pending_reports SET is_synced = 1, synced_at = ? WHERE id = ?;', [now, reportId]);
      return const Success(null);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de mise à jour du signalement: $e', stack));
    }
  }

  @override
  Future<Result<void, DatabaseFailure>> markReportsAsSyncedBatch(
    List<int> reportIds,
    DateTime syncedAt,
  ) async {
    if (reportIds.isEmpty) return const Success(null);
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final nowStr = syncedAt.toIso8601String();
      final placeholders = List.filled(reportIds.length, '?').join(', ');
      db.execute(
        'UPDATE pending_reports SET is_synced = 1, synced_at = ? WHERE id IN ($placeholders);',
        [nowStr, ...reportIds],
      );
      return const Success(null);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de la validation du lot de signalements: $e', stack));
    }
  }

  @override
  Future<Result<void, DatabaseFailure>> incrementReportsRetryCount(List<int> reportIds) async {
    if (reportIds.isEmpty) return const Success(null);
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final placeholders = List.filled(reportIds.length, '?').join(', ');
      db.execute(
        'UPDATE pending_reports SET retry_count = retry_count + 1 WHERE id IN ($placeholders);',
        reportIds,
      );
      return const Success(null);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de l\'incrémentation du retry: $e', stack));
    }
  }

  @override
  Future<Result<String?, DatabaseFailure>> getMetadata(String key) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final rows = db.select('SELECT value FROM sync_metadata WHERE key = ?;', [key]);
      if (rows.isEmpty) return const Success(null);
      return Success(rows.first['value'] as String?);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de lecture des métadonnées: $e', stack));
    }
  }

  @override
  Future<Result<void, DatabaseFailure>> setMetadata(String key, String value) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final now = DateTime.now().millisecondsSinceEpoch;
      db.execute(
        'INSERT OR REPLACE INTO sync_metadata (key, value, updated_at) VALUES (?, ?, ?);',
        [key, value, now],
      );
      return const Success(null);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec d\'écriture des métadonnées: $e', stack));
    }
  }

  @override
  Future<Result<void, DatabaseFailure>> applyFacilityPatch({
    required String patchId,
    required int version,
    required List<HealthProfessional> upserts,
    required List<int> deletions,
  }) async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final now = DateTime.now().millisecondsSinceEpoch;

      // Application des modifications/ajouts (upserts)
      for (final facility in upserts) {
        final jsonStr = jsonEncode(facility.toMap());
        db.execute(
          '''
          INSERT OR REPLACE INTO facility_patches (facility_id, patch_id, version, facility_json, is_deleted, applied_at)
          VALUES (?, ?, ?, ?, 0, ?);
          ''',
          [facility.id, patchId, version, jsonStr, now],
        );
      }

      // Application des suppressions logiques
      for (final id in deletions) {
        db.execute(
          '''
          INSERT OR REPLACE INTO facility_patches (facility_id, patch_id, version, facility_json, is_deleted, applied_at)
          VALUES (?, ?, ?, '', 1, ?);
          ''',
          [id, patchId, version, now],
        );
      }

      return const Success(null);
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec lors de l\'application du patch: $e', stack));
    }
  }

  @override
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getPatchedFacilities() async {
    final dbResult = _checkDb();
    if (dbResult.isFailure) return Failure(dbResult.errorOrNull!);
    final db = dbResult.dataOrNull!;

    try {
      final rows = db.select('SELECT facility_json FROM facility_patches WHERE is_deleted = 0 ORDER BY applied_at ASC;');
      final list = <HealthProfessional>[];

      for (final row in rows) {
        final jsonStr = row['facility_json'] as String;
        if (jsonStr.isEmpty) continue;
        final map = jsonDecode(jsonStr) as Map<String, dynamic>;
        final cat = (map['categorie'] as String?)?.toLowerCase() ?? '';
        if (cat.contains('pharmacie')) {
          list.add(Pharmacy.fromRow(map));
        } else {
          list.add(HealthProfessional.fromRow(map));
        }
      }

      return Success(List.unmodifiable(list));
    } catch (e, stack) {
      return Failure(DatabaseExecutionFailure('Échec de récupération des fiches patchées: $e', stack));
    }
  }

  Result<Database, DatabaseFailure> _checkDb() {
    if (!_isInitialized || _db == null) {
      return const Failure(DatabaseClosedFailure('Base de données utilisateur non initialisée ou fermée.'));
    }
    return Success(_db!);
  }

  @override
  void dispose() {
    try {
      _db?.dispose();
    } catch (_) {}
    _db = null;
    _isInitialized = false;
  }
}
