// Diagnostic: vérifie la casse des catégories DB vs les codes UI du FacetFilterBar,
// et mesure l'impact du filtre catégorie sur la recherche.
import 'package:sqlite3/sqlite3.dart';

void main() {
  final db = sqlite3.open('assets/data/sante_dz_bundled.db', mode: OpenMode.readOnly);

  // Codes utilisés par lib/features/map/widgets/facet_filter_bar.dart
  const uiCodes = [
    'Pharmacie',
    'Médecin Généraliste',
    'Hôpital',
    "Laboratoire d'analyses",
    'Dentiste',
    'Cardiologue',
    'Pédiatre',
    'Gynécologue',
    'Ophtalmologue',
  ];

  print('=== UI CODE -> MATCH COUNT (case-sensitive, as searchHybrid does) ===');
  for (final code in uiCodes) {
    final n = db.select('SELECT COUNT(*) AS c FROM facilities WHERE categorie = ?', [code]);
    final count = (n.first['c'] as num).toInt();
    print('  "$code" => $count');
  }

  print('=== COLLATE NOCASE variant ===');
  for (final code in uiCodes) {
    final n = db.select('SELECT COUNT(*) AS c FROM facilities WHERE categorie = ? COLLATE NOCASE', [code]);
    final count = (n.first['c'] as num).toInt();
    print('  "$code" => $count');
  }

  print('=== ACTUAL DISTINCT categories (lowercase, top 12) ===');
  for (final r in db.select('SELECT categorie, COUNT(*) c FROM facilities GROUP BY categorie ORDER BY c DESC LIMIT 12')) {
    print('  ${r['categorie']} => ${r['c']}');
  }

  print('=== Counts: total / distinct categories / wilayas ===');
  print('  total=${(db.select('SELECT COUNT(*) c FROM facilities').first['c'] as num).toInt()}');
  print('  distinct_cat=${(db.select('SELECT COUNT(DISTINCT categorie) c FROM facilities').first['c'] as num).toInt()}');
  print('  distinct_wilaya=${(db.select('SELECT COUNT(DISTINCT wilaya_code) c FROM facilities').first['c'] as num).toInt()}');

  print('=== Emergency detection sample: how many rows match "garde"/"urgence" ===');
  final em = db.select(
    "SELECT COUNT(*) c FROM facilities WHERE lower(nom) LIKE '%garde%' OR lower(nom) LIKE '%urgence%' OR lower(categorie) LIKE '%urgence%'",
  );
  print('  emergency-ish=${(em.first['c'] as num).toInt()}');

  print('=== distinct wilaya_code sample ===');
  final codes = db.select('SELECT DISTINCT wilaya_code FROM facilities ORDER BY wilaya_code LIMIT 10');
  print('  ${codes.map((r) => r['wilaya_code']).toList()}');

  db.dispose();
}
