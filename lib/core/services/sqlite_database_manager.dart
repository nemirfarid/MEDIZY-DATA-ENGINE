import 'dart:io';
import 'package:sqlite3/sqlite3.dart';
import '../errors/database_failure.dart';
import '../result/result.dart';

/// Gestionnaire du cycle de vie et de l'accès à la base de données SQLite locale (Offline-First)
class SqliteDatabaseManager {
  static final SqliteDatabaseManager _instance = SqliteDatabaseManager._internal();
  factory SqliteDatabaseManager() => _instance;
  SqliteDatabaseManager._internal();

  Database? _db;
  bool _isInitialized = false;
  String? _activePath;

  bool get isInitialized => _isInitialized && _db != null;
  String? get activePath => _activePath;

  /// Initialise la connexion SQLite en mode lecture seule stricte
  Result<void, DatabaseFailure> initialize({String? customPath}) {
    if (_isInitialized && _db != null) {
      return const Success(null);
    }

    try {
      final candidatePaths = [
        if (customPath != null) customPath,
        'assets/data/sante_dz_bundled.db',
        '../assets/data/sante_dz_bundled.db',
        r'D:\SANTE_DZ_EXPORTS\mobile\assets\data\sante_dz_bundled.db',
      ];

      String? resolvedPath;
      for (final p in candidatePaths) {
        if (File(p).existsSync()) {
          resolvedPath = p;
          break;
        }
      }

      if (resolvedPath == null) {
        return Failure(
          DatabaseNotFoundFailure(
            'Fichier SQLite introuvable parmi les chemins testés: $candidatePaths',
          ),
        );
      }

      // Ouverture en lecture seule (OpenMode.readOnly) pour sécurité absolue et concurrence maximale
      final db = sqlite3.open(resolvedPath, mode: OpenMode.readOnly);

      // Application des PRAGMA d'optimisation en mémoire
      try {
        db.execute('PRAGMA query_only = ON;');
        db.execute('PRAGMA mmap_size = 30000000;'); // ~30 Mo mmap I/O
        db.execute('PRAGMA cache_size = -8000;');    // ~8 Mo cache RAM
        db.execute('PRAGMA temp_store = MEMORY;');
      } catch (_) {
        // En cas de non support de certains pragmas selon l'environnement
      }

      _db = db;
      _activePath = resolvedPath;
      _isInitialized = true;
      return const Success(null);
    } catch (e, stack) {
      return Failure(
        DatabaseExecutionFailure(
          'Erreur lors de l\'ouverture de la base SQLite: $e',
          stack,
        ),
      );
    }
  }

  /// Obtient l'instance active de la base SQLite ou un DatabaseFailure typé
  Result<Database, DatabaseFailure> getDatabase() {
    if (!_isInitialized || _db == null) {
      return const Failure(
        DatabaseClosedFailure(
          'La base de données locale n\'est pas initialisée ou a été fermée.',
        ),
      );
    }
    return Success(_db!);
  }

  /// Libération propre de la base de données
  void dispose() {
    try {
      _db?.dispose();
    } catch (_) {}
    _db = null;
    _activePath = null;
    _isInitialized = false;
  }
}
