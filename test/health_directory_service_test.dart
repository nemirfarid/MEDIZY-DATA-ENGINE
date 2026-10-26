import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:sante_dz_medizy/core/errors/database_failure.dart';
import 'package:sante_dz_medizy/core/models/health_search_filter.dart';
import 'package:sante_dz_medizy/core/models/pharmacy.dart';
import 'package:sante_dz_medizy/core/services/sqlite_database_manager.dart';
import 'package:sante_dz_medizy/features/health_directory/services/health_directory_service.dart';

void main() {
  setUpAll(() {
    // Initialisation FFI pour environnement de test desktop Windows / Linux / macOS
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
  });

  group('Socle Offline-First SQLite - HealthDirectoryService Tests', () {
    late HealthDirectoryService service;
    const dbPath = 'assets/data/sante_dz_bundled.db';

    setUp(() async {
      service = HealthDirectoryService();
      final initResult = await service.initialize(customPath: dbPath);
      expect(initResult.isSuccess, isTrue, reason: 'L\'initialisation doit réussir');
    });

    tearDown(() {
      service.dispose();
    });

    test('1. Initialisation réussie de la base SQLite pré-packagée', () async {
      final manager = SqliteDatabaseManager();
      expect(manager.isInitialized, isTrue);
      expect(manager.activePath, contains('sante_dz_bundled.db'));

      final dbResult = manager.getDatabase();
      expect(dbResult.isSuccess, isTrue);
      expect(dbResult.dataOrNull, isNotNull);
    });

    test('2. Recherche filtrée par Wilaya et Spécialité (Wilaya 16 - Pharmacie)', () async {
      const filter = HealthSearchFilter(
        wilayaCode: '16',
        specialty: 'pharmacie',
        limit: 15,
      );

      final result = await service.search(filter);

      expect(result.isSuccess, isTrue);
      final professionals = result.dataOrNull!;
      expect(professionals.length, equals(15));

      for (final p in professionals) {
        expect(p.wilayaCode, equals('16'), reason: 'Le code wilaya doit être 16 (Alger)');
        expect(p.categorie.toLowerCase(), equals('pharmacie'));
        expect(p, isA<Pharmacy>(), reason: 'Une officine doit être instanciée en tant que Pharmacy');
        expect(p.nom.isNotEmpty, isTrue);
        expect(p.latitude, isNonZero);
        expect(p.longitude, isNonZero);
      }
    });

    test('3. Recherche affinée par Wilaya et Commune (Wilaya 01 - Adrar)', () async {
      const filter = HealthSearchFilter(
        wilayaCode: '01',
        commune: 'Adrar',
        limit: 20,
      );

      final result = await service.search(filter);

      expect(result.isSuccess, isTrue);
      final list = result.dataOrNull!;
      expect(list.isNotEmpty, isTrue);

      for (final item in list) {
        expect(item.wilayaCode, equals('01'));
        expect(item.commune.toLowerCase(), equals('adrar'));
      }
    });

    test('4. Recherche par mot-clé textuel (ex: "Pasteur")', () async {
      const filter = HealthSearchFilter(
        query: 'Pasteur',
        limit: 10,
      );

      final result = await service.search(filter);

      expect(result.isSuccess, isTrue);
      final list = result.dataOrNull!;
      expect(list.isNotEmpty, isTrue);

      for (final item in list) {
        final matches = item.nom.toLowerCase().contains('pasteur') ||
            item.commune.toLowerCase().contains('pasteur') ||
            (item.adresse?.toLowerCase().contains('pasteur') ?? false);
        expect(matches, isTrue, reason: 'Chaque résultat doit contenir la mention Pasteur');
      }
    });

    test('5. Couverture et liste exhaustive des 58 Wilayas algériennes', () async {
      final result = await service.getWilayas();

      expect(result.isSuccess, isTrue);
      final wilayas = result.dataOrNull!;
      expect(wilayas.length, equals(58), reason: 'L\'Algérie compte 58 wilayas administratives');

      final alger = wilayas.firstWhere((w) => w.code == '16');
      expect(alger.name.toLowerCase(), contains('alger'));
      expect(alger.totalFacilities, greaterThan(1000));

      final adrar = wilayas.firstWhere((w) => w.code == '01');
      expect(adrar.name.toLowerCase(), contains('adrar'));
    });

    test('6. Récupération des Communes pour une Wilaya spécifique (Wilaya 16)', () async {
      final result = await service.getCommunesForWilaya('16');

      expect(result.isSuccess, isTrue);
      final communes = result.dataOrNull!;
      expect(communes.isNotEmpty, isTrue);

      for (final c in communes) {
        expect(c.wilayaCode, equals('16'));
        expect(c.name.isNotEmpty, isTrue);
      }
    });

    test('7. Gestion défensive des erreurs - Tentative de requête sur service fermé', () async {
      final testManager = SqliteDatabaseManager();
      testManager.dispose(); // Fermeture volontaire

      final testService = HealthDirectoryService(dbManager: testManager);
      const filter = HealthSearchFilter(wilayaCode: '16', limit: 5);

      final result = await testService.search(filter);

      expect(result.isFailure, isTrue);
      expect(result.errorOrNull, isA<DatabaseClosedFailure>());
      expect(result.dataOrNull, isNull);
    });
  });
}
