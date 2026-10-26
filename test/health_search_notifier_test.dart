import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:sante_dz_medizy/core/errors/database_failure.dart';
import 'package:sante_dz_medizy/core/models/pharmacy.dart';
import 'package:sante_dz_medizy/core/utils/geo_calculator.dart';
import 'package:sante_dz_medizy/core/services/sqlite_database_manager.dart';
import 'package:sante_dz_medizy/features/health_directory/services/health_directory_service.dart';
import 'package:sante_dz_medizy/features/health_directory/state/health_search_notifier.dart';
import 'package:sante_dz_medizy/features/health_directory/state/health_search_state.dart';

void main() {
  setUpAll(() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
  });

  group('GeoCalculator - Tests Mathématiques de Haversine', () {
    test('1. Calcul de distance exacte entre Alger et Oran (~360 km)', () {
      const algerLat = 36.7538;
      const algerLon = 3.0588;
      const oranLat = 35.69765;
      const oranLon = -0.63374;

      final distance = GeoCalculator.distanceBetween(
        startLatitude: algerLat,
        startLongitude: algerLon,
        endLatitude: oranLat,
        endLongitude: oranLon,
      );

      expect(distance, greaterThan(350.0));
      expect(distance, lessThan(375.0));
    });

    test('2. Deux coordonnées identiques doivent donner une distance nulle (0.0 km)', () {
      final distance = GeoCalculator.distanceBetween(
        startLatitude: 36.75,
        startLongitude: 3.05,
        endLatitude: 36.75,
        endLongitude: 3.05,
      );
      expect(distance, equals(0.0));
    });
  });

  group('HealthSearchNotifier - Contrôleur Réactif Offline-First', () {
    late HealthDirectoryService directoryService;
    late HealthSearchNotifier notifier;
    const dbPath = 'assets/data/sante_dz_bundled.db';

    setUp(() async {
      directoryService = HealthDirectoryService();
      await directoryService.initialize(customPath: dbPath);
      notifier = HealthSearchNotifier(directoryService: directoryService);
      await notifier.initialize();
    });

    tearDown(() {
      notifier.dispose();
      directoryService.dispose();
    });

    test('3. Initialisation des référentiels (Wilayas et Spécialités)', () {
      expect(notifier.state.availableWilayas.length, equals(58));
      expect(notifier.state.availableSpecialties.isNotEmpty, isTrue);
      expect(notifier.state.status, equals(HealthSearchStatus.initial));
    });

    test('4. Cascading géographique : Wilaya -> Communes et réinitialisation de commune', () async {
      // 1. Sélection de la wilaya 01 (Adrar)
      await notifier.setWilaya('01');
      expect(notifier.state.filter.wilayaCode, equals('01'));
      expect(notifier.state.filter.commune, isNull);
      expect(notifier.state.availableCommunes.isNotEmpty, isTrue);
      expect(notifier.state.status, equals(HealthSearchStatus.success));

      // 2. Sélection de la commune d'Adrar
      await notifier.setCommune('Adrar');
      expect(notifier.state.filter.commune, equals('Adrar'));

      // 3. Changement vers la wilaya 16 (Alger) -> La commune précédente DOIT être réinitialisée
      await notifier.setWilaya('16');
      expect(notifier.state.filter.wilayaCode, equals('16'));
      expect(notifier.state.filter.commune, isNull, reason: 'La commune doit être réinitialisée lors du changement de wilaya');
      expect(notifier.state.availableCommunes.isNotEmpty, isTrue);
      final hasAlgerCommunes = notifier.state.availableCommunes.any((c) => c.wilayaCode == '16');
      expect(hasAlgerCommunes, isTrue);
    });

    test('5. Tri par proximité relative GPS (ordre croissant de distance)', () async {
      // Position de l'utilisateur à Alger Centre
      notifier.setUserLocation(latitude: 36.7538, longitude: 3.0588);
      expect(notifier.state.hasLocation, isTrue);

      await notifier.setWilaya('16');
      expect(notifier.state.status, equals(HealthSearchStatus.success));
      final results = notifier.state.results;
      expect(results.length, equals(20));

      // Vérification que chaque résultat a sa distance calculée et que la liste est triée
      for (var i = 0; i < results.length - 1; i++) {
        final currentDist = results[i].distanceKm;
        final nextDist = results[i + 1].distanceKm;

        expect(currentDist, isNotNull);
        expect(nextDist, isNotNull);
        expect(currentDist! <= nextDist!, isTrue,
            reason: 'Les résultats doivent être triés par distance croissante: $currentDist <= $nextDist');
      }
    });

    test('6. Filtrage exclusif des pharmacies de garde', () async {
      await notifier.setOnlyOnDutyPharmacies(true);
      await notifier.setWilaya('16');

      final results = notifier.state.results;
      for (final item in results) {
        expect(item, isA<Pharmacy>());
        final pharma = item as Pharmacy;
        expect(pharma.isOnDuty, isTrue, reason: 'Chaque résultat doit être une pharmacie de garde');
      }
    });

    test('7. Recherche textuelle débouncée', () async {
      // Déclenchement de la saisie avec un debounce court pour le test
      notifier.onSearchQueryChanged('Pasteur', debounceDuration: const Duration(milliseconds: 50));
      expect(notifier.state.filter.query, equals('Pasteur'));

      // Attente du déclenchement du debounce puis de la complétion de la requête SQLite
      await Future<void>.delayed(const Duration(milliseconds: 60));
      while (notifier.state.isLoading) {
        await Future<void>.delayed(const Duration(milliseconds: 20));
      }

      expect(notifier.state.status, equals(HealthSearchStatus.success));
      expect(notifier.state.results.isNotEmpty, isTrue);

      for (final item in notifier.state.results) {
        final matches = item.nom.toLowerCase().contains('pasteur') ||
            item.commune.toLowerCase().contains('pasteur') ||
            (item.adresse?.toLowerCase().contains('pasteur') ?? false);
        expect(matches, isTrue);
      }
    });

    test('8. Pagination infinie par lot de 20 fiches', () async {
      await notifier.setWilaya('16');
      expect(notifier.state.results.length, equals(20));
      expect(notifier.state.hasReachedMax, isFalse);

      await notifier.loadMore();
      expect(notifier.state.results.length, equals(40));
      expect(notifier.state.status, equals(HealthSearchStatus.success));
    });

    test('9. Interception et mapping strict des DatabaseFailure sans exception non gérée', () async {
      final failingManager = SqliteDatabaseManager();
      failingManager.dispose(); // Fermeture volontaire

      final failingService = HealthDirectoryService(dbManager: failingManager);
      final errorNotifier = HealthSearchNotifier(directoryService: failingService);

      await errorNotifier.search();

      expect(errorNotifier.state.status, equals(HealthSearchStatus.error));
      expect(errorNotifier.state.failure, isNotNull);
      expect(errorNotifier.state.failure, isA<DatabaseClosedFailure>());
      expect(errorNotifier.state.results.isEmpty, isTrue);

      errorNotifier.dispose();
    });
  });
}
