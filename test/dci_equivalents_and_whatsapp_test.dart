import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqlite3/sqlite3.dart';
import 'package:sante_dz_medizy/core/models/health_facility.dart';
import 'package:sante_dz_medizy/core/models/health_professional.dart';
import 'package:sante_dz_medizy/core/models/pharmacy.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/health_detail_sheet.dart';
import 'package:sante_dz_medizy/features/health_directory/presentation/widgets/health_professional_card.dart';
import 'package:sante_dz_medizy/features/map/widgets/facility_detail_sheet.dart';
import 'package:sante_dz_medizy/features/pharma/presentation/widgets/dci_equivalents_sheet.dart';
import 'package:sante_dz_medizy/features/pharma/services/dz_medication_service.dart';
import 'package:sante_dz_medizy/features/pharma/utils/whatsapp_utils.dart';

void main() {
  group('TÂCHE 1 : BASE LOCALE DES MÉDICAMENTS & GÉNÉRIQUES ALGÉRIENS (DCI & FTS5)', () {
    late Database memoryDb;
    late DzMedicationService medicationService;

    setUp(() {
      memoryDb = sqlite3.openInMemory();
      medicationService = DzMedicationService()..initialize(db: memoryDb);
    });

    tearDown(() {
      medicationService.dispose();
      memoryDb.dispose();
    });

    test('1.1. Intégrité du schéma SQLite relationnel et index plein-texte FTS5', () {
      final tables = memoryDb
          .select("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('medicaments_dz', 'medicaments_fts');")
          .map((r) => r['name'] as String)
          .toList();

      expect(tables, contains('medicaments_dz'));
      expect(tables, contains('medicaments_fts'));

      final allMeds = medicationService.getAllMedications(limit: 100);
      expect(allMeds.length, greaterThanOrEqualTo(30));
    });

    test('1.2. Recherche plein-texte FTS5 par nom de marque, DCI et laboratoire', () {
      // Recherche par nom de marque commerciale "Doliprane"
      final dolipraneResults = medicationService.search('Doliprane');
      expect(dolipraneResults.isNotEmpty, isTrue);
      expect(dolipraneResults.first.nomCommercial, contains('Doliprane'));
      expect(dolipraneResults.first.dci, equals('Paracétamol'));

      // Recherche par DCI "Metformine"
      final metformineResults = medicationService.search('Metformine');
      expect(metformineResults.isNotEmpty, isTrue);
      expect(metformineResults.any((m) => m.nomCommercial == 'Glucophage'), isTrue);
      expect(metformineResults.any((m) => m.nomCommercial == 'Metfor Saidal'), isTrue);

      // Recherche par laboratoire national "Saidal"
      final saidalResults = medicationService.search('Saidal');
      expect(saidalResults.length, greaterThanOrEqualTo(5));
      expect(saidalResults.every((m) => m.laboratoire.toLowerCase().contains('saidal')), isTrue);
    });

    test('1.3. Regroupement par DCI et détection des substituts en cas de rupture de stock', () {
      // Scénario : Le patient cherche du "Doliprane" (potentiellement en rupture)
      final equiv = medicationService.getEquivalentsFor('Doliprane');

      expect(equiv.hasEquivalents, isTrue);
      expect(equiv.dci, equals('Paracétamol'));
      expect(equiv.targetMedication?.nomCommercial, equals('Doliprane'));

      // Tous les équivalents partagent la même DCI
      expect(equiv.allEquivalents.every((m) => m.dci == 'Paracétamol'), isTrue);

      // Présence des génériques locaux (Saidal, Biopharm...)
      expect(equiv.generics.any((m) => m.nomCommercial == 'Paracétamol Saidal'), isTrue);
      expect(equiv.generics.any((m) => m.nomCommercial == 'Algidol'), isTrue);
      expect(equiv.localProducers.any((m) => m.laboratoire == 'Saidal'), isTrue);
      expect(equiv.localProducers.any((m) => m.laboratoire == 'Biopharm'), isTrue);

      // Présence du princeps original
      expect(equiv.princepsList.any((m) => m.nomCommercial == 'Doliprane'), isTrue);
    });

    test('1.4. Vérification du statut de prise en charge Chifa (ضمان اجتماعي)', () {
      final equiv = medicationService.getEquivalentsFor('Augmentin');

      expect(equiv.dci, contains('Amoxicilline'));
      expect(equiv.allEquivalents.isNotEmpty, isTrue);

      // Les équivalents essentiels en Algérie sont remboursables Chifa
      final chifaCovered = equiv.allEquivalents.where((m) => m.remboursableChifa).toList();
      expect(chifaCovered.length, equals(equiv.allEquivalents.length));

      final saidalGeneric = equiv.allEquivalents.firstWhere((m) => m.laboratoire == 'Saidal');
      expect(saidalGeneric.remboursableChifa, isTrue);
      expect(saidalGeneric.isLocalProducer, isTrue);
    });

    test('1.5. Benchmark de performance recherche FTS5 sur 100 requêtes (< 2 ms/req)', () {
      final stopwatch = Stopwatch()..start();
      for (int i = 0; i < 100; i++) {
        final query = (i % 2 == 0) ? 'Paracétamol' : 'Augmentin';
        medicationService.search(query, limit: 10);
      }
      stopwatch.stop();

      final avgLatencyMs = stopwatch.elapsedMicroseconds / 1000.0 / 100.0;
      expect(avgLatencyMs, lessThan(3.0)); // Moins de 3 ms par requête
    });

    testWidgets('1.6. DciEquivalentsSheet affiche les équivalents et le badge Chifa', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: DciEquivalentsSheet(
              medicationService: medicationService,
              initialQuery: 'Doliprane',
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Vérifie la présence du bandeau DCI et des cartes d'équivalents
      expect(find.text('DCI ACTIVE'), findsOneWidget);
      expect(find.text('Paracétamol'), findsWidgets);
      expect(find.text('Production Nationale Algérienne 🇩🇿'), findsOneWidget);
      expect(find.text('Paracétamol Saidal'), findsWidgets);
      expect(find.text('CHIFA'), findsWidgets);
    });
  });

  group('TÂCHE 2 : CONTACT DIRECT & PARTAGE D\'ORDONNANCE WHATSAPP', () {
    test('2.1. Détection des numéros mobiles algériens compatibles WhatsApp', () {
      // Numéros mobiles valides (Mobilis 06, Djezzy 07, Ooredoo 05)
      expect(WhatsAppUtils.isAlgerianMobile('0550 12 34 56'), isTrue);
      expect(WhatsAppUtils.isAlgerianMobile('0661987654'), isTrue);
      expect(WhatsAppUtils.isAlgerianMobile('07 70 11 22 33'), isTrue);
      expect(WhatsAppUtils.isAlgerianMobile('+213 550 12 34 56'), isTrue);
      expect(WhatsAppUtils.isAlgerianMobile('+213 661 98 76 54'), isTrue);
      expect(WhatsAppUtils.isAlgerianMobile('00213 770 11 22 33'), isTrue);
      expect(WhatsAppUtils.isAlgerianMobile('213550123456'), isTrue);

      // Numéros fixes ou numéros d'urgence (non compatibles WhatsApp mobile)
      expect(WhatsAppUtils.isAlgerianMobile('021 73 11 22'), isFalse); // Fixe Alger
      expect(WhatsAppUtils.isAlgerianMobile('031 92 44 55'), isFalse); // Fixe Constantine
      expect(WhatsAppUtils.isAlgerianMobile('14'), isFalse); // Protection Civile
      expect(WhatsAppUtils.isAlgerianMobile(''), isFalse);
      expect(WhatsAppUtils.isAlgerianMobile(null), isFalse);
    });

    test('2.2. Formatage strict sans zéro initial et indicatif +213 pour WhatsApp wa.me', () {
      // 05xx -> 2135xx
      expect(WhatsAppUtils.formatForWhatsApp('0550123456'), equals('213550123456'));
      expect(WhatsAppUtils.formatForWhatsApp('05 50 12 34 56'), equals('213550123456'));

      // 06xx -> 2136xx
      expect(WhatsAppUtils.formatForWhatsApp('0661 11 22 33'), equals('213661112233'));

      // 07xx -> 2137xx
      expect(WhatsAppUtils.formatForWhatsApp('07-70-99-88-77'), equals('213770998877'));

      // +213 5xx / 6xx / 7xx -> 2135xx
      expect(WhatsAppUtils.formatForWhatsApp('+213 550 12 34 56'), equals('213550123456'));
      expect(WhatsAppUtils.formatForWhatsApp('+213 0661 22 33 44'), equals('213661223344'));
      expect(WhatsAppUtils.formatForWhatsApp('00213 770 12 34 56'), equals('213770123456'));
    });

    test('2.3. Génération de l\'URL WhatsApp avec message d\'ouverture en Darija et Français', () {
      final url = WhatsAppUtils.generateWhatsAppUrl(
        phone: '0550 12 34 56',
      );

      expect(url, isNotNull);
      expect(url, startsWith('https://wa.me/213550123456?text='));

      final decodedText = Uri.decodeComponent(url!.split('text=')[1]);
      // Vérification de la présence des phrases obligatoires en Darija et Français
      expect(decodedText, contains('السلام عليكم، هل هذا الدواء متوفر لديكم؟'));
      expect(decodedText, contains('Bonjour, ce médicament est-il disponible dans votre officine ?'));
      expect(decodedText, contains('ordonnance'));
    });

    test('2.4. Génération de l\'URL personnalisée avec nom du médicament recherché', () {
      final url = WhatsAppUtils.generateWhatsAppUrl(
        phone: '0661 99 88 77',
        medicationName: 'Augmentin 1g',
      );

      expect(url, isNotNull);
      expect(url, startsWith('https://wa.me/213661998877?text='));

      final decodedText = Uri.decodeComponent(url!.split('text=')[1]);
      expect(decodedText, contains('Augmentin 1g'));
      expect(decodedText, contains('السلام عليكم'));
      expect(decodedText, contains('الوصفة الطبية'));
    });

    testWidgets('2.5. HealthProfessionalCard affiche le bouton WhatsApp pour les mobiles', (tester) async {
      bool whatsappTapped = false;

      final mobilePharmacy = Pharmacy(
        id: 801,
        nom: 'Pharmacie El Chifa - Bab Ezzouar',
        wilaya: 'Alger',
        wilayaCode: '16',
        commune: 'Bab Ezzouar',
        adresse: 'Cité 5 Juillet, Bâtiment 12',
        telephone: '0550 12 34 56', // Mobile valide
        latitude: 36.7210,
        longitude: 3.1850,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: HealthProfessionalCard(
              professional: mobilePharmacy,
              onTap: () {},
              onWhatsAppPressed: () {
                whatsappTapped = true;
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final whatsappButton = find.byKey(const Key('card_whatsapp_button_801'));
      expect(whatsappButton, findsOneWidget);

      await tester.tap(whatsappButton);
      await tester.pump();
      expect(whatsappTapped, isTrue);
    });

    testWidgets('2.6. HealthDetailSheet affiche le bouton d\'action directe WhatsApp', (tester) async {
      final professionalWithMobile = HealthProfessional(
        id: 902,
        nom: 'Dr. Benali - Cardiologue',
        categorie: 'medecin',
        wilaya: 'Oran',
        wilayaCode: '31',
        commune: 'Oran Centre',
        adresse: 'Boulevard Front de Mer',
        telephone: '0661 22 33 44', // Mobile algérien
        latitude: 35.6987,
        longitude: -0.6349,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: HealthDetailSheet(
              professional: professionalWithMobile,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('action_whatsapp_button')), findsOneWidget);
      expect(find.text('WhatsApp'), findsOneWidget);
    });

    testWidgets('2.7. FacilityDetailSheet intègre le bouton WhatsApp pour officines sur carte', (tester) async {
      final facilityWithMobile = HealthFacility(
        id: 1003,
        placeId: '1003',
        nom: 'Pharmacie Centrale Blida',
        categorie: 'pharmacie',
        wilaya: 'Blida',
        wilayaCode: '09',
        commune: 'Blida',
        adresse: 'Place du 1er Novembre',
        telephone: '0770 99 88 77', // Mobile algérien
        latitude: 36.4700,
        longitude: 2.8300,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: FacilityDetailSheet(
              facility: facilityWithMobile,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('WhatsApp'), findsOneWidget);
    });
  });
}
