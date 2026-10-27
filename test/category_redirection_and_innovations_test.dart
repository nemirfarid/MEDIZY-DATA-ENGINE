import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';
import 'package:sante_dz_medizy/core/models/health_facility.dart';
import 'package:sante_dz_medizy/core/models/health_professional.dart';
import 'package:sante_dz_medizy/core/models/health_search_filter.dart';
import 'package:sante_dz_medizy/core/models/pharmacy.dart';
import 'package:sante_dz_medizy/core/services/offline_health_search_service.dart';
import 'package:sante_dz_medizy/core/services/user_storage_service.dart';
import 'package:sante_dz_medizy/core/utils/geo_calculator.dart';
import 'package:sante_dz_medizy/features/emergency/presentation/widgets/sos_emergency_button.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/health_directory_map_view.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/health_filter_bar.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/health_professional_card.dart';
import 'package:sante_dz_medizy/features/health_directory/services/health_directory_service.dart';
import 'package:sante_dz_medizy/features/health_directory/state/health_search_notifier.dart';
import 'package:sante_dz_medizy/features/home/presentation/widgets/category_grid.dart';
import 'package:sante_dz_medizy/features/map/widgets/facet_filter_bar.dart';
import 'package:sante_dz_medizy/features/navigation/presentation/offline_compass_sheet.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  group('TÂCHE 1 : Normalisation des catégories & Transmission réactive', () {
    test('Les 11 catégories de CategoryGrid correspondent aux colonnes SQLite et Top Categories', () {
      const expectedCategories = [
        'dentiste',
        'pharmacie',
        'laboratoire',
        'imagerie',
        'pédiatre',
        'cardiologue',
        'généraliste',
        'clinique',
        'gynécologue',
        'ophtalmologue',
        'urgences',
      ];

      final gridSlugs = CategoryGrid.categories.map((c) => c['slug'] as String).toList();
      final facetCodes = FacetFilterBar.topCategories.map((c) => c['code']).toList();
      for (final cat in expectedCategories) {
        expect(gridSlugs.contains(cat), isTrue, reason: 'CategoryGrid doit contenir le slug $cat');
        expect(facetCodes.contains(cat), isTrue,
            reason: 'FacetFilterBar doit contenir le slug $cat');
      }
    });

    test('HealthSearchFilter et Notifier supportent le slug category de manière réactive', () {
      final filter = HealthSearchFilter(category: 'pédiatre');
      expect(filter.category, equals('pédiatre'));
      expect(filter.specialty, equals('pédiatre'));

      final copy = filter.copyWith(category: 'cardiologue');
      expect(copy.category, equals('cardiologue'));
      expect(copy.specialty, equals('cardiologue'));
    });

    testWidgets('HealthDirectoryMapView affiche le badge dismissible lorsque activeCategory est défini',
        (tester) async {
      bool cleared = false;
      final facilities = [
        HealthProfessional(
          id: 1,
          nom: 'Dr Amine Belkacem',
          categorie: 'Pédiatre',
          wilayaCode: '16',
          wilaya: 'Alger',
          commune: 'Hydra',
          latitude: 36.75,
          longitude: 3.05,
        ),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: HealthDirectoryMapView(
              facilities: facilities,
              activeCategory: 'pédiatre',
              enableTiles: false,
              onClearCategory: () => cleared = true,
              onFacilitySelected: (_) {},
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.textContaining('Pédiatres (1 résultats)'), findsOneWidget);
      expect(find.byKey(const Key('clear_directory_category_chip')), findsOneWidget);

      await tester.tap(find.byKey(const Key('clear_directory_category_chip')));
      await tester.pumpAndSettle();
      expect(cleared, isTrue);
    });
  });

  group('TÂCHE 2.1 : Bouton d\'Urgence Immédiate "SOS Santé 24/7"', () {
    late OfflineHealthSearchService searchService;

    setUp(() {
      searchService = OfflineHealthSearchService();
      searchService.initialize(customPath: 'assets/data/sante_dz_bundled.db');
    });

    tearDown(() {
      searchService.dispose();
    });

    test('searchSosEmergencies filtre les services à moins de 10 km et trie par Haversine', () {
      // Coordonnées Mostaganem Centre (35.9311, 0.0892)
      final emergencies = searchService.searchSosEmergencies(
        latitude: 35.9311,
        longitude: 0.0892,
        radiusKm: 10.0,
      );

      expect(emergencies.isNotEmpty, isTrue);
      // Vérification du tri par distance croissante
      for (int i = 0; i < emergencies.length - 1; i++) {
        expect(emergencies[i].distanceKm!, lessThanOrEqualTo(emergencies[i + 1].distanceKm!));
        expect(emergencies[i].distanceKm!, lessThanOrEqualTo(10.5));
      }
    });

    testWidgets('SosEmergencyButton et Sheet affichent les numéros 14 et 1548', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SosEmergencyButton(
                searchService: searchService,
                userPosition: const LatLng(35.9311, 0.0892),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byKey(const Key('sos_emergency_fab')), findsOneWidget);

      // Tap pour ouvrir la modal SOS
      await tester.tap(find.byKey(const Key('sos_emergency_fab')));
      await tester.pumpAndSettle();

      // Vérification des boutons d'appels d'urgence 14 et 1548
      expect(find.byKey(const Key('call_14_button')), findsOneWidget);
      expect(find.byKey(const Key('call_1548_button')), findsOneWidget);
      expect(find.textContaining('Protection Civile'), findsOneWidget);
      expect(find.textContaining('Police Secours'), findsOneWidget);
    });
  });

  group('TÂCHE 2.2 : Filtre exclusif "Convention Chifa" (ضمان اجتماعي)', () {
    test('HealthFacility hasChifa identifie correctement les établissements conventionnés', () {
      final pharmaChifa = HealthFacility(
        id: 1,
        nom: 'Pharmacie Centrale',
        categorie: 'Pharmacie',
        wilaya: 'Alger',
        wilayaCode: '16',
        commune: 'Alger Centre',
        latitude: 36.7,
        longitude: 3.0,
      );
      expect(pharmaChifa.hasChifa, isTrue);

      final laboChifa = HealthFacility(
        id: 2,
        nom: 'Laboratoire d\'analyses médicales',
        categorie: 'Laboratoire',
        wilaya: 'Oran',
        wilayaCode: '31',
        commune: 'Oran',
        latitude: 35.7,
        longitude: -0.6,
      );
      expect(laboChifa.hasChifa, isTrue);
    });

    testWidgets('HealthProfessionalCard affiche le badge vert CHIFA', (tester) async {
      final pharma = Pharmacy(
        id: 101,
        nom: 'Pharmacie de Garde El Chifa',
        wilayaCode: '16',
        wilaya: 'Alger',
        commune: 'Bab El Oued',
        latitude: 36.78,
        longitude: 3.05,
        acceptsChifa: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: HealthProfessionalCard(
              professional: pharma,
              onTap: () {},
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byKey(const Key('badge_chifa_101')), findsOneWidget);
      expect(find.text('CHIFA ✓'), findsOneWidget);
    });

    testWidgets('HealthFilterBar permet de basculer le filtre Chifa', (tester) async {
      final notifier = HealthSearchNotifier(
        directoryService: HealthDirectoryService(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: HealthFilterBar(
              notifier: notifier,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      final chifaChip = find.byKey(const Key('chifa_filter_chip'));
      expect(chifaChip, findsOneWidget);

      await tester.ensureVisible(chifaChip);
      await tester.pumpAndSettle();

      await tester.tap(chifaChip);
      await tester.pumpAndSettle();
      expect(notifier.state.onlyChifa, isTrue);
    });
  });

  group('TÂCHE 2.3 : Mode "Orientation Boussole & Guidage Hors-Ligne"', () {
    test('GeoCalculator calcule le relèvement en degrés et la direction cardinale', () {
      // Vers le Nord pur
      final bearingNorth = GeoCalculator.bearingBetween(
        startLatitude: 36.0,
        startLongitude: 3.0,
        endLatitude: 37.0,
        endLongitude: 3.0,
      );
      expect(bearingNorth, closeTo(0.0, 1.0));
      expect(GeoCalculator.cardinalDirection(bearingNorth), equals('N'));

      // Vers l'Est pur
      final bearingEast = GeoCalculator.bearingBetween(
        startLatitude: 36.0,
        startLongitude: 3.0,
        endLatitude: 36.0,
        endLongitude: 4.0,
      );
      expect(bearingEast, closeTo(90.0, 1.0));
      expect(GeoCalculator.cardinalDirection(bearingEast), equals('E'));

      // Vers le Sud pur
      final bearingSouth = GeoCalculator.bearingBetween(
        startLatitude: 36.0,
        startLongitude: 3.0,
        endLatitude: 35.0,
        endLongitude: 3.0,
      );
      expect(bearingSouth, closeTo(180.0, 1.0));
      expect(GeoCalculator.cardinalDirection(bearingSouth), equals('S'));
    });

    testWidgets('OfflineCompassSheet affiche le cap et la distance dynamique hors-ligne', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (ctx) => ElevatedButton(
                onPressed: () {
                  OfflineCompassSheet.show(
                    ctx,
                    targetName: 'Clinique El Hana',
                    targetCategory: 'Clinique',
                    targetLat: 36.76,
                    targetLon: 3.06,
                    userPosition: const LatLng(36.75, 3.05),
                  );
                },
                child: const Text('Ouvrir Boussole'),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();
      await tester.tap(find.text('Ouvrir Boussole'));
      await tester.pumpAndSettle();

      expect(find.text('Clinique El Hana'), findsOneWidget);
      expect(find.textContaining('100% HORS-LIGNE'), findsOneWidget);
      expect(find.text('DISTANCE'), findsOneWidget);
      expect(find.text('CAP BOUSSOLE'), findsOneWidget);
      expect(find.textContaining('km'), findsWidgets);
    });
  });

  group('TÂCHE 2.4 : Favoris et Carnet Médical Local Privé', () {
    test('UserStorageService sauvegarde et récupère une note personnelle privée', () async {
      final storage = UserStorageService.inMemory();

      final doc = HealthProfessional(
        id: 42,
        nom: 'Dr Bouzid',
        categorie: 'Cardiologue',
        wilayaCode: '16',
        wilaya: 'Alger',
        commune: 'Kouba',
        latitude: 36.7,
        longitude: 3.0,
      );
      await storage.toggleFavorite(doc);

      // Ajout d'une note personnelle privée
      await storage.savePersonalNote(42, 'Secrétaire joignable le matin de 8h à 11h');

      final noteRes = await storage.getPersonalNote(42);
      expect(noteRes.dataOrNull, equals('Secrétaire joignable le matin de 8h à 11h'));
    });
  });
}
