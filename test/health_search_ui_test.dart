import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/screens/health_search_screen.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/health_detail_sheet.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/health_professional_card.dart';
import 'package:sante_dz_medizy/features/health_directory/services/health_directory_service.dart';
import 'package:sante_dz_medizy/features/health_directory/state/health_search_notifier.dart';

void main() {
  setUpAll(() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }
  });

  group('HealthSearchScreen & UI Widgets Tests', () {
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

    testWidgets('1. Rendu initial : Champ de recherche, filtres et bascule de vue', (tester) async {
      // Configuration de l'écran dans une MaterialApp de test
      await tester.pumpWidget(
        MaterialApp(
          home: HealthSearchScreen(
            notifier: notifier,
            enableMapTiles: false,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Vérification des éléments d'interface principaux
      expect(find.text('Santé DZ / Annuaire National'), findsOneWidget);
      expect(find.byKey(const Key('search_text_field')), findsOneWidget);
      expect(find.byKey(const Key('toggle_view_mode_button')), findsOneWidget);
      expect(find.byKey(const Key('wilaya_dropdown')), findsOneWidget);
      expect(find.byKey(const Key('commune_dropdown')), findsOneWidget);
      expect(find.byKey(const Key('duty_filter_chip')), findsOneWidget);
    });

    testWidgets('2. Filtrage interactif par Wilaya et mise à jour réactive de la liste', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: HealthSearchScreen(
            notifier: notifier,
            enableMapTiles: false,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Sélection de la wilaya 16 (Alger)
      await notifier.setWilaya('16');
      await tester.pumpAndSettle();

      // Vérification que la liste des résultats s'est chargée avec des cartes
      expect(find.byKey(const Key('results_list_view')), findsOneWidget);
      expect(find.byType(HealthProfessionalCard), findsWidgets);

      // Vérification qu'au moins une carte est affichée avec sa commune
      final firstCard = tester.widget<HealthProfessionalCard>(find.byType(HealthProfessionalCard).first);
      expect(firstCard.professional.wilayaCode, equals('16'));
      expect(firstCard.professional.nom.isNotEmpty, isTrue);
    });

    testWidgets('3. Ouverture de la fiche détaillée modale et interaction avec les actions', (tester) async {
      bool callTriggered = false;
      bool navTriggered = false;

      await notifier.setWilaya('16');

      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              return Scaffold(
                body: ElevatedButton(
                  key: const Key('open_sheet_button'),
                  onPressed: () {
                    final facility = notifier.state.results.first;
                    HealthDetailSheet.show(
                      context,
                      facility,
                      onLaunchCall: (phone) async {
                        callTriggered = true;
                      },
                      onLaunchNavigation: (lat, lon) async {
                        navTriggered = true;
                      },
                    );
                  },
                  child: const Text('Ouvrir Fiche'),
                ),
              );
            },
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Clic pour ouvrir la fiche détaillée modale
      await tester.tap(find.byKey(const Key('open_sheet_button')));
      await tester.pumpAndSettle();

      // Vérification de la présence des sections détaillées
      expect(find.byType(HealthDetailSheet), findsOneWidget);
      expect(find.text('Adresse & Commune'), findsOneWidget);
      expect(find.text('Coordonnées GPS'), findsOneWidget);
      expect(find.byKey(const Key('action_nav_button')), findsOneWidget);

      // Clic sur le bouton d'itinéraire GPS
      await tester.tap(find.byKey(const Key('action_nav_button')));
      await tester.pumpAndSettle();
      expect(navTriggered, isTrue);

      // Clic sur le bouton d'appel si présent
      if (find.byKey(const Key('action_call_button')).evaluate().isNotEmpty) {
        await tester.tap(find.byKey(const Key('action_call_button')));
        await tester.pumpAndSettle();
        expect(callTriggered, isTrue);
      }
    });

    testWidgets('4. Bascule réactive entre vue Liste et vue Cartographique (FlutterMap)', (tester) async {
      // Injection de la position utilisateur et chargement de résultats
      notifier.setUserLocation(latitude: 36.7538, longitude: 3.0588);
      await notifier.setWilaya('16');

      await tester.pumpWidget(
        MaterialApp(
          home: HealthSearchScreen(
            notifier: notifier,
            enableMapTiles: false,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Vue liste active initialement
      expect(find.byKey(const Key('results_list_view')), findsOneWidget);
      expect(find.byKey(const Key('health_directory_flutter_map')), findsNothing);

      // Clic sur le bouton de bascule vers la carte
      await tester.tap(find.byKey(const Key('toggle_view_mode_button')));
      await tester.pumpAndSettle();

      // La carte FlutterMap doit maintenant être affichée
      expect(find.byKey(const Key('health_directory_flutter_map')), findsOneWidget);
      expect(find.byKey(const Key('results_list_view')), findsNothing);

      // Clic à nouveau sur le bouton pour revenir à la liste
      await tester.tap(find.byKey(const Key('toggle_view_mode_button')));
      await tester.pumpAndSettle();

      // Retour fluide sur la vue liste
      expect(find.byKey(const Key('results_list_view')), findsOneWidget);
      expect(find.byKey(const Key('health_directory_flutter_map')), findsNothing);
    });
  });
}
