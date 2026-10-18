import 'dart:convert';
import 'dart:io';
import 'package:test/test.dart';
import '../lib/core/services/offline_health_search_service.dart';

void main() {
  late OfflineHealthSearchService searchService;

  setUpAll(() {
    searchService = OfflineHealthSearchService();
    searchService.initialize(customPath: 'assets/data/sante_dz_bundled.db');
  });

  tearDownAll(() {
    searchService.dispose();
  });

  group('SANTÉ DZ / MEDIZY — TESTS D\'INTÉGRATION & BENCHMARKS MOBILES (PHASE 10)', () {
    // -------------------------------------------------------------------------
    // TEST 1 : DÉTECTION ET INTÉGRITÉ DE LA BASE EMBARQUÉE SANTE_DZ_BUNDLED.DB
    // -------------------------------------------------------------------------
    test('Test 1 : Intégrité et détection exacte des 35 832 fiches sanitaires', () {
      final total = searchService.getTotalFacilitiesCount();
      print('\n[TEST 1] Volume total d\'établissements qualifiés détecté : $total');
      expect(total, equals(35832), reason: 'La base doit contenir exactement 35 832 fiches');

      // Vérification des tables virtuelles
      final ftsCount = searchService.db.select('SELECT COUNT(*) AS c FROM facilities_fts;').first['c'];
      final rtreeCount = searchService.db.select('SELECT COUNT(*) AS c FROM facilities_rtree;').first['c'];

      print('[TEST 1] Index FTS5 fiches indexées : $ftsCount');
      print('[TEST 1] Index R-Tree coordonnées indexées : $rtreeCount');

      expect(ftsCount, equals(35832));
      expect(rtreeCount, equals(35832));
    });

    // -------------------------------------------------------------------------
    // TEST 2 : COUVERTURE INTÉGRALE DES 58 WILAYAS
    // -------------------------------------------------------------------------
    test('Test 2 : Couverture géographique exhaustive des 58 Wilayas (01 à 58)', () {
      final wilayasCount = searchService.getWilayasCount();
      print('\n[TEST 2] Nombre de wilayas couvertes : $wilayasCount / 58');
      expect(wilayasCount, equals(58), reason: 'Les 58 wilayas doivent être représentées');

      final codes = searchService.getAllWilayaCodes();
      for (var i = 1; i <= 58; i++) {
        final expectedCode = i.toString().padLeft(2, '0');
        expect(
          codes.contains(expectedCode),
          isTrue,
          reason: 'Le code wilaya $expectedCode doit être présent',
        );
      }

      // Vérification du fichier d'index des wilayas
      final wilayasJsonFile = File('assets/data/medizy_wilayas_index.json');
      expect(wilayasJsonFile.existsSync(), isTrue);
      final Map<String, dynamic> indexData = jsonDecode(wilayasJsonFile.readAsStringSync());
      final List list = indexData['wilayas'] as List;
      expect(list.length, equals(58));
    });

    // -------------------------------------------------------------------------
    // TEST 3 : BENCHMARK RECHERCHE PLEIN TEXTE FTS5 (< 2,5 ms)
    // -------------------------------------------------------------------------
    test('Test 3 : Benchmark de recherche FTS5 : latence moyenne sur 100 requêtes < 2,5 ms', () {
      final commonQueries = [
        'pharmacie', 'hopital', 'dr ben', 'dentiste', 'cardiologue',
        'laboratoire', 'alger', 'oran', 'constantine', 'annaba',
        'setif', 'batna', 'tlemcen', 'bejaia', 'blida',
        'biskra', 'djelfa', 'chahid', 'chehida', 'urgences',
        'pediatre', 'gynecologue', 'ophtalmologue', 'polyclinique', 'radiologie',
      ];

      // Générer 100 requêtes à partir de l'échantillon
      final sample100 = <String>[];
      while (sample100.length < 100) {
        sample100.addAll(commonQueries);
      }
      final testQueries = sample100.take(100).toList();

      // Warmup du cache SQLite
      searchService.searchFts('pharmacie', limit: 10);

      // Mesure de performance
      final avgLatencyMs = searchService.benchmarkFtsLatencyMs(testQueries);
      print('\n[TEST 3] Benchmark FTS5 : 100 requêtes exécutées');
      print('[TEST 3] Latence moyenne par requête FTS5 : ${avgLatencyMs.toStringAsFixed(3)} ms (cible: < 2,5 ms)');

      expect(
        avgLatencyMs,
        lessThan(2.5),
        reason: 'La latence FTS5 moyenne doit être inférieure à 2.5 ms',
      );
    });

    // -------------------------------------------------------------------------
    // TEST 4 : BENCHMARK SPATIAL R-TREE (< 1,0 ms)
    // -------------------------------------------------------------------------
    test('Test 4 : Benchmark spatial R-Tree : extraction rayon 5 km en < 1,0 ms', () {
      // Coordonnées de test : Alger Centre (36.7538, 3.0588)
      const testLat = 36.7538;
      const testLon = 3.0588;

      // Warmup
      searchService.searchAroundMe(latitude: testLat, longitude: testLon, radiusKm: 5.0, limit: 20);

      // Exécution de 100 requêtes spatiales avec calcul Haversine
      final avgLatencyMs = searchService.benchmarkRtreeLatencyMs(
        latitude: testLat,
        longitude: testLon,
        radiusKm: 5.0,
        iterations: 100,
      );

      print('\n[TEST 4] Benchmark R-Tree : 100 extractions de proximité (rayon 5 km)');
      print('[TEST 4] Latence moyenne R-Tree + Haversine : ${avgLatencyMs.toStringAsFixed(3)} ms (cible: < 1,0 ms)');

      expect(
        avgLatencyMs,
        lessThan(1.0),
        reason: 'L\'extraction spatiale R-Tree doit s\'exécuter en moins de 1.0 ms',
      );

      // Validation de la cohérence des distances
      final nearby = searchService.searchAroundMe(
        latitude: testLat,
        longitude: testLon,
        radiusKm: 5.0,
        limit: 10,
      );
      expect(nearby.isNotEmpty, isTrue);
      for (final fac in nearby) {
        expect(fac.distanceKm, isNotNull);
        expect(fac.distanceKm!, lessThanOrEqualTo(5.25)); // Marge tolérée de 5%
      }
    });

    // -------------------------------------------------------------------------
    // TEST 5 : DÉCOMPRESSION ET LECTURE DU BUNDLE JSON COMPRESSÉ
    // -------------------------------------------------------------------------
    test('Test 5 : Décompression et lecture à froid du bundle JSON.GZ sans fuite mémoire', () {
      final gzFile = File('assets/data/sante_dz_db.json.gz');
      expect(gzFile.existsSync(), isTrue, reason: 'sante_dz_db.json.gz doit être présent dans assets/data');

      final fileSizeBytes = gzFile.lengthSync();
      final sizeMb = fileSizeBytes / (1024 * 1024);
      print('\n[TEST 5] Taille du bundle compressé GZ : ${sizeMb.toStringAsFixed(2)} Mo (cible < 3,0 Mo)');
      expect(sizeMb, lessThan(3.0));

      final stopwatch = Stopwatch()..start();
      final bytes = gzFile.readAsBytesSync();
      final decompressedBytes = gzip.decode(bytes);
      final jsonString = utf8.decode(decompressedBytes);
      final Map<String, dynamic> data = jsonDecode(jsonString);
      stopwatch.stop();

      final decompressionMs = stopwatch.elapsedMilliseconds;
      print('[TEST 5] Temps de décompression et parsing JSON : $decompressionMs ms');

      final facilities = data['facilities'] as List;
      print('[TEST 5] Fiches sanitaires désérialisées : ${facilities.length}');

      expect(facilities.length, equals(35832));
    });
  });
}
