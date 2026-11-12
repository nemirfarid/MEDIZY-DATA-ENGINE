with open('lib/core/services/offline_health_search_service.dart', 'r', encoding='utf-8') as f:
    c = f.read()

new_method = '''  /// Recupere la liste ordonnee et dedoublee des communes pour une Wilaya donnee
  List<String> getCommunesForWilaya(String? wilayaCode) {
    if (wilayaCode == null || wilayaCode.isEmpty) return [];
    try {
      final results = db.select(
        'SELECT DISTINCT commune FROM facilities WHERE wilaya_code = ? AND commune IS NOT NULL AND TRIM(commune) != "" ORDER BY commune ASC;',
        [wilayaCode],
      );
      return results.map((r) => (r['commune'] as String).trim()).where((c) => c.isNotEmpty).toList();
    } catch (_) {
      return [];
    }
  }

'''

if 'getCommunesForWilaya' not in c:
    target = 'List<HealthFacility> searchHybrid({'
    idx = c.find(target)
    c = c[:idx] + new_method + c[idx:]
    with open('lib/core/services/offline_health_search_service.dart', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Added getCommunesForWilaya successfully')
else:
    print('getCommunesForWilaya already exists')

