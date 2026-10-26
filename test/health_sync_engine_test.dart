import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:sante_dz_medizy/core/models/crowd_report.dart';
import 'package:sante_dz_medizy/core/models/delta_patch.dart';
import 'package:sante_dz_medizy/core/models/health_professional.dart';
import 'package:sante_dz_medizy/core/models/pharmacy.dart';
import 'package:sante_dz_medizy/core/services/delta_patch_service.dart';
import 'package:sante_dz_medizy/core/services/sync_transport.dart';
import 'package:sante_dz_medizy/core/services/user_storage_service.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/sync_status_badge.dart';
import 'package:sante_dz_medizy/features/health_directory/state/health_sync_engine.dart';

void main() {
  setUpAll(() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
  });

  group('HealthSyncEngine & DeltaPatchService Tests', () {
    const testDbPath = 'test_sync_user_data.db';
    late UserStorageService storageService;
    late HealthDeltaPatchService patchService;
    late MockSyncTransport transport;
    late HealthSyncEngine syncEngine;

    setUp(() async {
      final f = File(testDbPath);
      if (f.existsSync()) f.deleteSync();

      storageService = UserStorageService();
      await storageService.initialize(customPath: testDbPath);
      patchService = HealthDeltaPatchService(storageService: storageService);
      transport = MockSyncTransport();
      syncEngine = HealthSyncEngine(
        storageService: storageService,
        patchService: patchService,
        transport: transport,
      );
      await syncEngine.initialize();
    });

    tearDown(() {
      syncEngine.dispose();
      storageService.dispose();
      final f = File(testDbPath);
      if (f.existsSync()) f.deleteSync();
    });

    test('1. Expédition par lots des signalements en attente et validation atomique', () async {
      // Insertion de 3 signalements locaux
      for (int i = 1; i <= 3; i++) {
        await storageService.enqueueReport(
          CrowdReport(
            facilityId: 100 + i,
            facilityName: 'Établissement #$i',
            reportType: ReportType.wrongPhoneNumber,
            suggestedPhone: '02100000$i',
            description: 'Signalement de test $i',
            createdAt: DateTime.now().toUtc(),
          ),
        );
      }

      await syncEngine.initialize();
      expect(syncEngine.pendingCount, 3);
      expect(syncEngine.status, SyncStatus.online);

      // Déclenchement de la synchronisation
      final result = await syncEngine.synchronize();
      expect(result.isSuccess, isTrue);
      expect(result.dataOrNull, isTrue);

      // Vérification du transport : 1 lot de 3 signalements expédié
      expect(transport.sentBatches.length, 1);
      expect(transport.sentBatches.first.length, 3);

      // Vérification dans SQLite : plus aucun signalement en attente
      final pendingAfter = await storageService.getPendingReports();
      expect(pendingAfter.isSuccess, isTrue);
      expect(pendingAfter.dataOrNull, isEmpty);

      // Le compteur du moteur réactif est remis à 0 et le statut est au succès
      expect(syncEngine.pendingCount, 0);
      expect(syncEngine.status, SyncStatus.success);
    });

    test('2. Gestion des pannes réseau et incrémentation de retry_count', () async {
      // Insertion de 2 signalements
      await storageService.enqueueReport(
        CrowdReport(
          facilityId: 201,
          facilityName: 'Cabinet Dr A',
          reportType: ReportType.wrongAddress,
          createdAt: DateTime.now().toUtc(),
        ),
      );
      await storageService.enqueueReport(
        CrowdReport(
          facilityId: 202,
          facilityName: 'Cabinet Dr B',
          reportType: ReportType.closedPermanently,
          createdAt: DateTime.now().toUtc(),
        ),
      );

      await syncEngine.initialize();
      expect(syncEngine.pendingCount, 2);

      // Simulation d'une panne réseau
      transport.shouldFail = true;

      // Première tentative : échec
      final syncResult1 = await syncEngine.synchronize();
      expect(syncResult1.isFailure, isTrue);
      expect(syncEngine.status, SyncStatus.error);
      expect(syncEngine.lastErrorMessage, contains('Échec réseau'));

      // Vérification SQLite : retry_count incrémenté à 1 pour les deux items
      final pending1 = await storageService.getPendingReports();
      expect(pending1.dataOrNull!.length, 2);
      expect(pending1.dataOrNull![0].retryCount, 1);
      expect(pending1.dataOrNull![1].retryCount, 1);
      expect(pending1.dataOrNull![0].isSynced, isFalse);

      // Deuxième tentative : nouvel échec -> retry_count passe à 2
      final syncResult2 = await syncEngine.synchronize();
      expect(syncResult2.isFailure, isTrue);
      final pending2 = await storageService.getPendingReports();
      expect(pending2.dataOrNull![0].retryCount, 2);
      expect(pending2.dataOrNull![1].retryCount, 2);

      // Rétablissement du réseau
      transport.shouldFail = false;
      final syncResult3 = await syncEngine.synchronize();
      expect(syncResult3.isSuccess, isTrue);

      // Tout a été envoyé et marqué synchronisé
      final pendingFinal = await storageService.getPendingReports();
      expect(pendingFinal.dataOrNull, isEmpty);
      expect(syncEngine.pendingCount, 0);
      expect(syncEngine.status, SyncStatus.success);
    });

    test('3. Application atomique d\'un DeltaPatch incrémental (upsert, mise à jour, suppression logique)', () async {
      // État initial de la version du jeu de données
      final vInit = await patchService.getCurrentDatasetVersion();
      expect(vInit.dataOrNull, 1);

      final newDoctor = HealthProfessional(
        id: 88801,
        nom: 'Dr. Amine Benali',
        categorie: 'Cardiologie',
        wilaya: 'Alger',
        wilayaCode: '16',
        commune: 'Hydra',
        telephone: '021601122',
        latitude: 36.75,
        longitude: 3.05,
      );

      final updatedPharmacy = Pharmacy(
        id: 99901,
        nom: 'Pharmacie Centrale El Madania',
        wilaya: 'Alger',
        wilayaCode: '16',
        commune: 'El Madania',
        telephone: '021279988',
        latitude: 36.74,
        longitude: 3.06,
        isOnDuty: true,
        acceptsChifa: true,
      );

      const obsoleteFacilityId = 77701;

      final patch = DeltaPatch(
        patchId: 'patch-alger-2026-v2',
        targetDatasetVersion: 2,
        issuedAt: DateTime.parse('2026-10-25T08:30:00Z'),
        upserts: [newDoctor, updatedPharmacy],
        deletions: [obsoleteFacilityId],
      );

      transport.nextPatch = patch;

      // Déclenchement de la synchronisation
      final syncRes = await syncEngine.synchronize();
      expect(syncRes.isSuccess, isTrue);

      // Vérification du versionnage et de l'audit
      final vAfter = await patchService.getCurrentDatasetVersion();
      expect(vAfter.dataOrNull, 2);

      final lastSyncUtc = await patchService.getLastSyncUtc();
      expect(lastSyncUtc.isSuccess, isTrue);
      expect(lastSyncUtc.dataOrNull, DateTime.parse('2026-10-25T08:30:00Z'));

      // Vérification des fiches patchées enregistrées
      final patchedRes = await patchService.getPatchedFacilities();
      expect(patchedRes.isSuccess, isTrue);
      final patchedList = patchedRes.dataOrNull!;
      expect(patchedList.length, 2);

      final doctorFound = patchedList.firstWhere((f) => f.id == 88801);
      expect(doctorFound.nom, 'Dr. Amine Benali');
      expect(doctorFound.categorie, 'Cardiologie');

      final pharmacyFound = patchedList.firstWhere((f) => f.id == 99901) as Pharmacy;
      expect(pharmacyFound.nom, 'Pharmacie Centrale El Madania');
      expect(pharmacyFound.telephone, '021279988');
      expect(pharmacyFound.isOnDuty, isTrue);
      expect(pharmacyFound.acceptsChifa, isTrue);
    });

    testWidgets('4. Réactivité du badge SyncStatusBadge et interaction tactile', (tester) async {
      // 1. Initialement connecté avec 0 signalement
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            appBar: AppBar(
              actions: [
                SyncStatusBadge(syncEngine: syncEngine),
              ],
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Icône connectée visible
      expect(find.byIcon(Icons.cloud_done_rounded), findsOneWidget);

      // 2. Bascule en mode hors-ligne
      syncEngine.setOnline(false);
      await tester.pumpAndSettle();
      expect(find.byIcon(Icons.cloud_off_rounded), findsOneWidget);

      // 3. Reconnexion et ajout d'un signalement en attente
      syncEngine.setOnline(true);
      await storageService.enqueueReport(
        CrowdReport(
          facilityId: 301,
          facilityName: 'Clinique Chiffa',
          reportType: ReportType.other,
          createdAt: DateTime.now().toUtc(),
        ),
      );
      await syncEngine.initialize();
      await tester.pumpAndSettle();

      // Le badge avec le compteur '1' est visible
      expect(find.text('1'), findsOneWidget);

      // 4. Clic sur le badge pour synchroniser
      await tester.tap(find.byType(SyncStatusBadge));
      await tester.pump(); // Démarre la sync (syncing)
      await tester.pumpAndSettle(); // Fin de la sync

      // Le signalement a été envoyé, le compteur disparaît
      expect(syncEngine.pendingCount, 0);
      expect(find.text('1'), findsNothing);
      expect(find.byIcon(Icons.cloud_done_rounded), findsOneWidget);
    });
  });
}
