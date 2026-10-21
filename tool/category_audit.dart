// Diagnostic: audit complet des catégories DB vs les codes UI du FacetFilterBar.
// Usage: dart run tool/category_audit.dart <fichier_sortie>
import 'dart:io';
import 'package:sqlite3/sqlite3.dart';

void main(List<String> args) {
  final out = StringBuffer();
  void w(Object o) => out.writeln(o.toString());

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

  w('=== A. MATCH EXACT (comme searchHybrid today) ===');
  for (final code in uiCodes) {
    final n = db.select('SELECT COUNT(*) AS c FROM facilities WHERE categorie = ?', [code]);
    w('  "$code" => ${(n.first['c'] as num).toInt()}');
  }

  w('');
  w('=== B. MATCH COLLATE NOCASE ===');
  for (final code in uiCodes) {
    final n = db.select('SELECT COUNT(*) AS c FROM facilities WHERE categorie = ? COLLATE NOCASE', [code]);
    w('  "$code" => ${(n.first['c'] as num).toInt()}');
  }

  w('');
  w('=== C. TOUTES LES CATEGORIES DISTINCTES (nom => count) ===');
  final all = db.select('SELECT categorie, COUNT(*) c FROM facilities GROUP BY categorie ORDER BY c DESC');
  for (final r in all) {
    w('  ${r['categorie']} => ${r['c']}');
  }
  w('  TOTAL DISTINCT = ${all.length}');

  w('');
  w('=== D. MATCH PAR PREFIXE (LIKE) pour chaque code UI ===');
  for (final code in uiCodes) {
    final needle = code.toLowerCase();
    final n = db.select(
      "SELECT COUNT(*) c FROM facilities WHERE lower(categorie) LIKE ?",
      ['%$needle%'],
    );
    final hits = db.select(
      "SELECT DISTINCT categorie FROM facilities WHERE lower(categorie) LIKE ?",
      ['%$needle%'],
    );
    w('  "$code" => ${(n.first['c'] as num).toInt()}  [${hits.map((r) => r['categorie']).join(', ')}]');
  }

  w('');
  w('=== E. VOLUMES ===');
  w('  total=${(db.select('SELECT COUNT(*) c FROM facilities').first['c'] as num).toInt()}');
  w('  distinct_cat=${(db.select('SELECT COUNT(DISTINCT categorie) c FROM facilities').first['c'] as num).toInt()}');
  w('  distinct_wilaya=${(db.select('SELECT COUNT(DISTINCT wilaya_code) c FROM facilities').first['c'] as num).toInt()}');

  w('');
  w('=== F. WILAYA CODES ===');
  w('  ${db.select('SELECT DISTINCT wilaya_code FROM facilities ORDER BY wilaya_code').map((r) => r['wilaya_code']).join(",")}');

  db.dispose();

  final path = args.isEmpty ? 'tmp_audit.txt' : args[0];
  File(path).writeAsStringSync(out.toString());
}
