import 'package:sqlite3/sqlite3.dart';

/// Outil de diagnostic : dump des catégories réelles du référentiel SQLite embarqué.
void main() {
  final db = sqlite3.open('assets/data/sante_dz_bundled.db', mode: OpenMode.readOnly);
  print('=== TABLES ===');
  for (final r in db.select("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")) {
    print(r['name']);
  }
  print('=== CATEGORIES (count) ===');
  for (final r in db.select('SELECT categorie, COUNT(*) c FROM facilities GROUP BY categorie ORDER BY c DESC;')) {
    print('${r['categorie']} => ${r['c']}');
  }
  print('=== SAMPLE ROW ===');
  for (final r in db.select('SELECT * FROM facilities LIMIT 2;')) {
    print(r);
  }
  print('=== COLUMNS ===');
  for (final r in db.select('PRAGMA table_info(facilities);')) {
    print(r);
  }
  db.dispose();
}
