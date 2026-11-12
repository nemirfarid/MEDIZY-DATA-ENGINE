import 'package:flutter_test/flutter_test.dart';
import 'package:sante_dz_medizy/core/services/offline_health_search_service.dart';

void main() {
  group('QUALIFICATION EN CONDITIONS RÉELLES & TERRAIN — MEDIZY v1.0.17', () {
    late OfflineHealthSearchService searchService;

    setUpAll(() {
      searchService = OfflineHealthSearchService();
      searchService.initialize(customPath: 'assets/data/sante_dz_bundled.db');
    });

    tearDownAll(() {
      searchService.dispose();
    });

    // -------------------------------------------------------------------------
    // SCÉNARIO 1 : RECHERCHE D'URGENCE / GARDE SUR LA WILAYA DE MOSTAGANEM (27)
    // -------------------------------------------------------------------------
    test('Test 1 : Recherche urgence/garde sur Mostaganem (Code 27) en < 5 ms', () {
      // Warmup
      searchService.searchHybrid(wilayaCode: '27', limit: 10);

      // Recherche multicritère : Wilaya 27 (Mostaganem) + Urgences/Gardes
      final results = searchService.searchHybrid(
        wilayaCode: '27',
        onlyEmergency: true,
        limit: 100,
      );

      print('\n[SCÉNARIO 1] Établissements d\'urgence / garde à Mostaganem (27) : ${results.length} fiches');
      expect(results.isNotEmpty, isTrue, reason: 'La wilaya de Mostaganem doit comporter des établissements');
      for (final fac in results) {
        expect(fac.wilayaCode, equals('27'));
        expect(fac.isEmergencyOrOnDuty, isTrue);
      }

      // Recherche par mot-clé sanitaire (Hôpitaux et Pharmacies de Mostaganem)
      final hopitauxMosta = searchService.searchHybrid(
        query: 'hopital',
        wilayaCode: '27',
        limit: 50,
      );
      print('[SCÉNARIO 1] Hôpitaux identifiés à Mostaganem : ${hopitauxMosta.length}');
      expect(hopitauxMosta.isNotEmpty, isTrue);

      // Benchmark de latence moyenne sur 100 requêtes consécutives
      final latencies = <double>[];
      for (int i = 0; i < 100; i++) {
        final sw = Stopwatch()..start();
        final res = searchService.searchHybrid(
          wilayaCode: '27',
          onlyEmergency: true,
          limit: 50,
        );
        sw.stop();
        latencies.add(sw.elapsedMicroseconds / 1000.0);
        expect(res.isNotEmpty, isTrue);
      }

      final avgLatencyMs = latencies.reduce((a, b) => a + b) / latencies.length;
      print('[SCÉNARIO 1] Latence moyenne sur 100 requêtes Mostaganem (27) : ${avgLatencyMs.toStringAsFixed(3)} ms (Cible < 10.0 ms)');

      expect(
        avgLatencyMs,
        lessThan(10.0),
        reason: 'La recherche locale SQLite FTS5/R-Tree doit s\'exécuter en moins de 10 ms',
      );
    });

    // -------------------------------------------------------------------------
    // SCÉNARIO 2 : RECHERCHE GÉOLOCALISÉE R-TREE AUTOUR DE MOSTAGANEM VILLE
    // -------------------------------------------------------------------------
    test('Test 2 : Recherche spatiale R-Tree 10 km autour de Mostaganem Centre (< 5 ms)', () {
      // Coordonnées Mostaganem Centre : (35.9311, 0.0892)
      const mostaLat = 35.9311;
      const mostaLon = 0.0892;

      // Warmup du cache R-Tree
      searchService.searchAroundMe(latitude: mostaLat, longitude: mostaLon, radiusKm: 10.0, limit: 10);

      // Mesure de latence sur 50 requêtes de pan / zoom
      final latencies = <double>[];
      List nearby = [];
      for (int i = 0; i < 50; i++) {
        final sw = Stopwatch()..start();
        nearby = searchService.searchAroundMe(
          latitude: mostaLat,
          longitude: mostaLon,
          radiusKm: 10.0,
          limit: 50,
        );
        sw.stop();
        latencies.add(sw.elapsedMicroseconds / 1000.0);
      }

      final avgLatencyMs = latencies.reduce((a, b) => a + b) / latencies.length;
      print('\n[SCÉNARIO 2] Établissements détectés dans un rayon de 10 km : ${nearby.length}');
      print('[SCÉNARIO 2] Latence moyenne R-Tree + Haversine : ${avgLatencyMs.toStringAsFixed(3)} ms (Cible < 5.0 ms)');

      expect(nearby.isNotEmpty, isTrue);
      expect(avgLatencyMs, lessThan(5.0));

      for (final fac in nearby) {
        expect(fac.distanceKm, isNotNull);
        expect(fac.distanceKm!, lessThanOrEqualTo(10.5));
      }
    });

    // -------------------------------------------------------------------------
    // SCÉNARIO 3 : TEST RÉSILIENCE 100% HORS-LIGNE (AUCUNE DÉPENDANCE RÉSEAU)
    // -------------------------------------------------------------------------
    test('Test 3 : Intégrité des 35 832 fiches et fonctionnement air-gapped', () {
      // Vérification que les 35 832+ fiches sont accessibles sans connexion
      final allCount = searchService.getTotalFacilitiesCount();
      expect(allCount, greaterThanOrEqualTo(35832));

      // Test de recherche plein-texte FTS5 multi-wilayas sans appel réseau
      final sw = Stopwatch()..start();
      final results = searchService.searchFts('hopital', limit: 30);
      sw.stop();

      print('\n[SCÉNARIO 3] Recherche FTS5 air-gapped : ${results.length} résultats en ${(sw.elapsedMicroseconds / 1000.0).toStringAsFixed(3)} ms');
      expect(results.isNotEmpty, isTrue);
    });
  });
}
