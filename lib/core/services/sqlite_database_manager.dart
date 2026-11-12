import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart' show getDatabasesPath;
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

  /// Version courante de la base de données embarquée.
  /// Incrémenter à chaque mise à jour du fichier sante_dz_bundled.db
  /// pour forcer la recopie depuis les assets et l'écrasement de l'ancienne base.
  static const int _dbVersion = 36;

  bool get isInitialized => _isInitialized && _db != null;
  String? get activePath => _activePath;

  /// Initialise la connexion SQLite en mode lecture seule stricte.
  /// Copie la base depuis les assets vers getDatabasesPath() si nécessaire,
  /// et force la recopie si la version a changé (écrase l'ancienne base).
  /// Si customPath est fourni, l'utilise directement (pour les tests).
  Future<Result<void, DatabaseFailure>> initialize({String? customPath}) async {
    if (_isInitialized && _db != null) {
      return const Success(null);
    }

    try {
      String dbFilePath;

      if (customPath != null) {
        // Utiliser le chemin fourni directement (mode test)
        dbFilePath = customPath;
      } else {
        // Répertoire standard sqflite (getDatabasesPath())
        final dbPath = await getDatabasesPath();
        final dbDir = Directory(dbPath);
        if (!dbDir.existsSync()) {
          dbDir.createSync(recursive: true);
        }

        dbFilePath = p.join(dbPath, 'sante_dz_bundled.db');
        final versionFile = File(p.join(dbPath, 'db_version.txt'));

        // Vérifier si une recopie est nécessaire
        bool needsCopy = !File(dbFilePath).existsSync();
        if (!needsCopy && versionFile.existsSync()) {
          final storedVersion = int.tryParse(versionFile.readAsStringSync().trim()) ?? 0;
          if (storedVersion < _dbVersion) {
            needsCopy = true;
          }
        } else if (!versionFile.existsSync()) {
          needsCopy = true;
        }

        if (needsCopy) {
          // Fermer la connexion existante avant d'écraser le fichier
          try {
            _db?.dispose();
          } catch (_) {}
          _db = null;
          _isInitialized = false;

          // Supprimer l'ancien fichier de base dans getDatabasesPath()
          if (File(dbFilePath).existsSync()) {
            File(dbFilePath).deleteSync();
          }

          // Supprimer aussi toute base résiduelle dans le répertoire documents (ancienne version)
          try {
            final documentsDir = await getApplicationDocumentsDirectory();
            final oldDbDir = Directory(p.join(documentsDir.path, 'db'));
            if (oldDbDir.existsSync()) {
              final oldDbFile = File(p.join(oldDbDir.path, 'sante_dz_bundled.db'));
              if (oldDbFile.existsSync()) {
                oldDbFile.deleteSync();
              }
              final oldVersionFile = File(p.join(oldDbDir.path, 'db_version.txt'));
              if (oldVersionFile.existsSync()) {
                oldVersionFile.deleteSync();
              }
            }
          } catch (_) {}

          // Copier depuis les assets
          final ByteData data = await rootBundle.load('assets/data/sante_dz_bundled.db');
          final List<int> bytes = data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
          await File(dbFilePath).writeAsBytes(bytes, flush: true);

          // Écrire la version
          await versionFile.writeAsString('$_dbVersion');
        }
      }

      // Ouverture en lecture seule
      final db = sqlite3.open(dbFilePath, mode: OpenMode.readOnly);

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
      _activePath = dbFilePath;
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
