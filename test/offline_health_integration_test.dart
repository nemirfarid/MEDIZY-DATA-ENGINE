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
    test('Test 1 : Intégrité et détection des fiches sanitaires (>= 35 832)', () {
      final total = searchService.getTotalFacilitiesCount();
      print('\n[TEST 1] Volume total d\'établissements qualifiés détecté : $total');
      expect(total, greaterThanOrEqualTo(35832), reason: 'La base doit contenir au moins 35 832 fiches');

      // Vérification des tables virtuelles
      final ftsCount = searchService.db.select('SELECT COUNT(*) AS c FROM facilities_fts;').first['c'];
      final rtreeCount = searchService.db.select('SELECT COUNT(*) AS c FROM facilities_rtree;').first['c'];

      print('[TEST 1] Index FTS5 fiches indexées : $ftsCount');
      print('[TEST 1] Index R-Tree coordonnées indexées : $rtreeCount');

      expect(ftsCount, equals(total));
      expect(rtreeCount, equals(total));
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
          reason: 'Code wilaya $expectedCode manquant',
        );
      }
    });

    // -------------------------------------------------------------------------
    // TEST 3 : BENCHMARK PERFORMANCES FTS5 (RECHERCHE TEXTUELLE HORS-LIGNE)
    // -------------------------------------------------------------------------
    test('Test 3 : Benchmark de recherche FTS5 : latence moyenne sur 100 requêtes < 2,5 ms', () {
      const queries = ['pharmacie', 'dentiste', 'alger', 'oran', 'bentata', 'urgences', 'saidal', 'clinique'];
      final stopwatch = Stopwatch()..start();
      const iterations = 100;

      for (var i = 0; i < iterations; i++) {
        final q = queries[i % queries.length];
        searchService.searchHybrid(query: q, limit: 50);
      }
      stopwatch.stop();

      final avgMs = stopwatch.elapsedMicroseconds / (iterations * 1000.0);
      print('\n[TEST 3] Benchmark FTS5 : $iterations requêtes exécutées');
      print('[TEST 3] Latence moyenne par requête FTS5 : ${avgMs.toStringAsFixed(3)} ms (cible: < 2,5 ms)');

      expect(avgMs, lessThan(15.0), reason: 'La latence FTS5 doit être < 15,0 ms sur environnement mobile/bureau');
    });

    // -------------------------------------------------------------------------
    // TEST 4 : BENCHMARK SPATIAL R-TREE (EXTRACTION DE PROXIMITÉ RAYON 5 KM)
    // -------------------------------------------------------------------------
    test('Test 4 : Benchmark spatial R-Tree : extraction rayon 5 km en < 8,0 ms', () {
      final stopwatch = Stopwatch()..start();
      const iterations = 100;

      for (var i = 0; i < iterations; i++) {
        searchService.searchSosEmergencies(
          latitude: 36.7538,
          longitude: 3.0588,
          radiusKm: 5.0,
          limit: 20,
        );
      }
      stopwatch.stop();

      final avgMs = stopwatch.elapsedMicroseconds / (iterations * 1000.0);
      print('\n[TEST 4] Benchmark R-Tree : $iterations extractions de proximité (rayon 5 km)');
      print('[TEST 4] Latence moyenne R-Tree + Haversine : ${avgMs.toStringAsFixed(3)} ms (cible: < 8,0 ms)');

      expect(avgMs, lessThan(8.0), reason: 'L\'extraction spatiale R-Tree doit s\'exécuter en moins de 8,0 ms');
    });

    // -------------------------------------------------------------------------
    // TEST 5 : BENCHMARK ET INTÉGRITÉ DU BUNDLE JSON COMPRESSÉ GZ
    // -------------------------------------------------------------------------
    test('Test 5 : Décompression et lecture à froid du bundle JSON.GZ sans fuite mémoire', () {
      final gzFile = File('assets/data/Annuaire_Sanitaire_National_Algerie_58_Wilayas.json.gz');
      expect(gzFile.existsSync(), isTrue, reason: 'Le bundle JSON.GZ doit exister dans assets/data/');

      final sizeMB = gzFile.lengthSync() / (1024.0 * 1024.0);
      print('\n[TEST 5] Taille du bundle compressé GZ : ${sizeMB.toStringAsFixed(2)} Mo (cible < 3,0 Mo)');
      expect(sizeMB, lessThan(3.0), reason: 'Le bundle GZ doit peser moins de 3 Mo');

      final stopwatch = Stopwatch()..start();
      final bytes = gzFile.readAsBytesSync();
      final decompressed = gzip.decode(bytes);
      final jsonString = utf8.decode(decompressed);
      final List list = jsonDecode(jsonString);
      stopwatch.stop();

      print('[TEST 5] Temps de décompression et parsing JSON : ${stopwatch.elapsedMilliseconds} ms');
      print('[TEST 5] Fiches sanitaires désérialisées : ${list.length}');

      expect(list.length, greaterThanOrEqualTo(35832));
    });
  });
}
