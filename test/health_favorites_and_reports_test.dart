import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:sante_dz_medizy/core/models/crowd_report.dart';
import 'package:sante_dz_medizy/core/models/health_professional.dart';
import 'package:sante_dz_medizy/core/services/user_storage_service.dart';
import 'package:sante_dz_medizy/features/health_directory/state/health_favorites_notifier.dart';

void main() {
  setUpAll(() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
  });

  group('UserStorageService & HealthFavoritesNotifier Tests', () {
    const testDbPath = 'test_user_data.db';
    late UserStorageService storageService;
    late HealthFavoritesNotifier favoritesNotifier;

    final sampleFacility = HealthProfessional(
      id: 99901,
      nom: 'Pharmacie Centrale El Madania',
      categorie: 'pharmacie',
      wilaya: 'Alger',
      wilayaCode: '16',
      commune: 'El Madania',
      adresse: '12 Rue des Frères Mokhtari',
      telephone: '021278899',
      latitude: 36.7420,
      longitude: 3.0590,
    );

    setUp(() async {
      // Purge du fichier temporaire de test
      final f = File(testDbPath);
      if (f.existsSync()) f.deleteSync();

      storageService = UserStorageService();
      await storageService.initialize(customPath: testDbPath);
      favoritesNotifier = HealthFavoritesNotifier(storageService: storageService);
      await favoritesNotifier.initialize();
    });

    tearDown(() {
      favoritesNotifier.dispose();
      storageService.dispose();
      final f = File(testDbPath);
      if (f.existsSync()) f.deleteSync();
    });

    test('1. Persistance atomique des favoris (ajout, isFavorite, liste, suppression)', () async {
      // Initialement non favori
      final initCheck = await storageService.isFavorite(sampleFacility.id);
      expect(initCheck.dataOrNull, isFalse);

      // Ajout en favori
      final addResult = await storageService.toggleFavorite(sampleFacility);
      expect(addResult.isSuccess, isTrue);
      expect(addResult.dataOrNull, isTrue, reason: 'Doit retourner true quand l\'élément est ajouté');

      // Vérification immédiate
      final afterAdd = await storageService.isFavorite(sampleFacility.id);
      expect(afterAdd.dataOrNull, isTrue);

      // Récupération de la liste des favoris
      final listResult = await storageService.getFavorites();
      expect(listResult.isSuccess, isTrue);
      expect(listResult.dataOrNull!.length, equals(1));
      expect(listResult.dataOrNull!.first.nom, equals('Pharmacie Centrale El Madania'));

      // Suppression du favori
      final removeResult = await storageService.toggleFavorite(sampleFacility);
      expect(removeResult.isSuccess, isTrue);
      expect(removeResult.dataOrNull, isFalse, reason: 'Doit retourner false quand l\'élément est retiré');

      final afterRemove = await storageService.isFavorite(sampleFacility.id);
      expect(afterRemove.dataOrNull, isFalse);

      final emptyList = await storageService.getFavorites();
      expect(emptyList.dataOrNull!.isEmpty, isTrue);
    });

    test('2. Rotation et plafonnement de l\'historique des consultations à 20 entrées max', () async {
      // Insertion de 25 établissements distincts
      for (var i = 1; i <= 25; i++) {
        final fac = HealthProfessional(
          id: 1000 + i,
          nom: 'Cabinet Médical N°$i',
          categorie: 'cabinet médical',
          wilaya: 'Alger',
          wilayaCode: '16',
          commune: 'Kouba',
          latitude: 36.72,
          longitude: 3.08,
        );
        await storageService.recordView(fac);
      }

      final historyResult = await storageService.getRecentViews(limit: 20);
      expect(historyResult.isSuccess, isTrue);
      final history = historyResult.dataOrNull!;

      // La taille doit être strictement plafonnée à 20
      expect(history.length, equals(20), reason: 'L\'historique ne doit jamais dépasser 20 fiches');

      // Le dernier inséré (N°25) doit être en tête de liste (LIFO)
      expect(history.first.id, equals(1025));
      expect(history.first.nom, equals('Cabinet Médical N°25'));

      // Les 5 plus anciens (1001 à 1005) doivent avoir été purgés
      final ids = history.map((f) => f.id).toSet();
      expect(ids.contains(1001), isFalse);
      expect(ids.contains(1002), isFalse);
      expect(ids.contains(1005), isFalse);
      expect(ids.contains(1006), isTrue);
    });

    test('3. Mise en file d\'attente transactionnelle d\'un signalement collaboratif (CrowdReport)', () async {
      final report = CrowdReport(
        facilityId: sampleFacility.id,
        facilityName: sampleFacility.nom,
        reportType: ReportType.modifiedHours,
        description: 'Fermé le samedi après-midi',
        suggestedPhone: '021279900',
        createdAt: DateTime.now().toUtc(),
        isSynced: false,
      );

      final enqueueResult = await storageService.enqueueReport(report);
      expect(enqueueResult.isSuccess, isTrue);
      final savedReport = enqueueResult.dataOrNull!;
      expect(savedReport.id, isNotNull);
      expect(savedReport.facilityName, equals('Pharmacie Centrale El Madania'));
      expect(savedReport.isSynced, isFalse);

      // Récupération des signalements en attente de synchronisation
      final pendingResult = await storageService.getPendingReports();
      expect(pendingResult.isSuccess, isTrue);
      final pendingList = pendingResult.dataOrNull!;
      expect(pendingList.length, equals(1));
      expect(pendingList.first.reportType, equals(ReportType.modifiedHours));
      expect(pendingList.first.description, contains('Fermé le samedi'));

      // Marquage comme synchronisé
      await storageService.markReportAsSynced(savedReport.id!);
      final afterSync = await storageService.getPendingReports();
      expect(afterSync.dataOrNull!.isEmpty, isTrue, reason: 'Le signalement synchronisé ne doit plus être pending');
    });

    test('4. Contrôleur réactif HealthFavoritesNotifier et cache O(1) pour l\'IHM', () async {
      int notifyCount = 0;
      favoritesNotifier.addListener(() {
        notifyCount++;
      });

      expect(favoritesNotifier.isFavorite(sampleFacility.id), isFalse);

      // Ajout via le notifier (mise à jour optimiste + notification)
      final toggleAdd = await favoritesNotifier.toggleFavorite(sampleFacility);
      expect(toggleAdd.dataOrNull, isTrue);
      expect(favoritesNotifier.isFavorite(sampleFacility.id), isTrue);
      expect(favoritesNotifier.favoriteIds.contains(sampleFacility.id), isTrue);
      expect(favoritesNotifier.favorites.length, equals(1));
      expect(notifyCount, greaterThanOrEqualTo(1));

      // Retrait via le notifier
      final toggleRemove = await favoritesNotifier.toggleFavorite(sampleFacility);
      expect(toggleRemove.dataOrNull, isFalse);
      expect(favoritesNotifier.isFavorite(sampleFacility.id), isFalse);
      expect(favoritesNotifier.favorites.isEmpty, isTrue);
    });
  });
}
