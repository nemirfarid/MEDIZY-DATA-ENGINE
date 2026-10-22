import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

/// Service de favoris et récents 100% hors-ligne.
///
/// Stocke dans une base SQLite locale (séparée de la base nationale en lecture seule)
/// située dans le répertoire documents de l'application.
///
/// Tables :
///   - user_saved_facilities : favoris et récents de l'utilisateur
class FavoritesService {
  static final FavoritesService _instance = FavoritesService._internal();
  factory FavoritesService() => _instance;

  Database? _db;
  bool _isInitialized = false;

  FavoritesService._internal();

  /// Initialise la base de données favorites.
  Future<void> init() async {
    if (_isInitialized && _db != null) return;

    final docsDir = await getApplicationDocumentsDirectory();
    final dbPath = join(docsDir.path, 'medizy_favorites.db');

    _db = await openDatabase(
      dbPath,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE user_saved_facilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_id INTEGER NOT NULL,
            nom TEXT NOT NULL,
            categorie TEXT NOT NULL,
            wilaya_code TEXT NOT NULL,
            wilaya TEXT NOT NULL,
            commune TEXT NOT NULL,
            telephone TEXT,
            adresse TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            source TEXT,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            is_recent INTEGER NOT NULL DEFAULT 0,
            saved_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(facility_id)
          );
        ''');
        await db.execute('''
          CREATE INDEX idx_facilities_favorite ON user_saved_facilities(is_favorite);
        ''');
        await db.execute('''
          CREATE INDEX idx_facilities_recent ON user_saved_facilities(is_recent);
        ''');
        await db.execute('''
          CREATE INDEX idx_facilities_wilaya ON user_saved_facilities(wilaya_code);
        ''');
      },
    );

    _isInitialized = true;
  }

  Database get db {
    if (!_isInitialized || _db == null) {
      throw StateError('FavoritesService non initialisé. Appeler init() au préalable.');
    }
    return _db!;
  }

  /// Bascule le statut favori d'un établissement.
  /// Retourne true si l'établissement est maintenant favori.
  Future<bool> toggleFavorite({
    required int facilityId,
    required String nom,
    required String categorie,
    required String wilayaCode,
    required String wilaya,
    required String commune,
    String? telephone,
    String? adresse,
    required double latitude,
    required double longitude,
    String? source,
  }) async {
    final existing = await db.query(
      'user_saved_facilities',
      where: 'facility_id = ?',
      whereArgs: [facilityId],
    );

    final now = DateTime.now().toIso8601String();

    if (existing.isNotEmpty) {
      final currentFavorite = (existing.first['is_favorite'] as int) == 1;
      final newFavorite = !currentFavorite;
      await db.update(
        'user_saved_facilities',
        {
          'is_favorite': newFavorite ? 1 : 0,
          'updated_at': now,
          if (!newFavorite) 'is_recent': 1,
        },
        where: 'facility_id = ?',
        whereArgs: [facilityId],
      );
      return newFavorite;
    } else {
      await db.insert(
        'user_saved_facilities',
        {
          'facility_id': facilityId,
          'nom': nom,
          'categorie': categorie,
          'wilaya_code': wilayaCode,
          'wilaya': wilaya,
          'commune': commune,
          'telephone': telephone,
          'adresse': adresse,
          'latitude': latitude,
          'longitude': longitude,
          'source': source,
          'is_favorite': 1,
          'is_recent': 1,
          'saved_at': now,
          'updated_at': now,
        },
      );
      return true;
    }
  }

  /// Vérifie si un établissement est favori.
  Future<bool> isFavorite(int facilityId) async {
    final rows = await db.query(
      'user_saved_facilities',
      where: 'facility_id = ? AND is_favorite = 1',
      whereArgs: [facilityId],
    );
    return rows.isNotEmpty;
  }

  /// Récupère tous les favoris, triés par date de sauvegarde décroissante.
  Future<List<Map<String, dynamic>>> getFavorites() async {
    final rows = await db.query(
      'user_saved_facilities',
      where: 'is_favorite = 1',
      orderBy: 'saved_at DESC',
    );
    return rows;
  }

  /// Récupère les 10 derniers établissements consultés (récents).
  Future<List<Map<String, dynamic>>> getRecents({int limit = 10}) async {
    final rows = await db.query(
      'user_saved_facilities',
      where: 'is_recent = 1',
      orderBy: 'updated_at DESC',
      limit: limit,
    );
    return rows;
  }

  /// Marque un établissement comme récent (consulté).
  Future<void> markRecent({
    required int facilityId,
    required String nom,
    required String categorie,
    required String wilayaCode,
    required String wilaya,
    required String commune,
    String? telephone,
    String? adresse,
    required double latitude,
    required double longitude,
    String? source,
  }) async {
    final existing = await db.query(
      'user_saved_facilities',
      where: 'facility_id = ?',
      whereArgs: [facilityId],
    );

    final now = DateTime.now().toIso8601String();

    if (existing.isNotEmpty) {
      await db.update(
        'user_saved_facilities',
        {
          'is_recent': 1,
          'updated_at': now,
          'nom': nom,
          'categorie': categorie,
          'wilaya_code': wilayaCode,
          'wilaya': wilaya,
          'commune': commune,
          'telephone': telephone,
          'adresse': adresse,
          'latitude': latitude,
          'longitude': longitude,
          'source': source,
        },
        where: 'facility_id = ?',
        whereArgs: [facilityId],
      );
    } else {
      await db.insert(
        'user_saved_facilities',
        {
          'facility_id': facilityId,
          'nom': nom,
          'categorie': categorie,
          'wilaya_code': wilayaCode,
          'wilaya': wilaya,
          'commune': commune,
          'telephone': telephone,
          'adresse': adresse,
          'latitude': latitude,
          'longitude': longitude,
          'source': source,
          'is_favorite': 0,
          'is_recent': 1,
          'saved_at': now,
          'updated_at': now,
        },
      );
    }
  }

  /// Retire un établissement des favoris.
  Future<void> removeFavorite(int facilityId) async {
    await db.update(
      'user_saved_facilities',
      {'is_favorite': 0},
      where: 'facility_id = ?',
      whereArgs: [facilityId],
    );
  }

  /// Nombre total de favoris.
  Future<int> getFavoriteCount() async {
    final result = await db.rawQuery(
      'SELECT COUNT(*) as c FROM user_saved_facilities WHERE is_favorite = 1',
    );
    return (result.first['c'] as int);
  }

  /// Ferme la base de données.
  Future<void> close() async {
    await _db?.close();
    _db = null;
    _isInitialized = false;
  }
}
