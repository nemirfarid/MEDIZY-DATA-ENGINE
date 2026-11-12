import 'dart:io';
import 'package:sqlite3/sqlite3.dart';
import 'package:sqlite3_flutter_libs/sqlite3_flutter_libs.dart';

void main() {
  // Initialize sqlite3
  sqlite3.flutterInitLibs();
  
  final db = sqlite3.open("C:/SANTE_DZ_SCRAPER/assets/data/sante_dz_bundled.db");
  
  // Check R-Tree table schema
  final schemaResult = db.select("SELECT sql FROM sqlite_master WHERE name='facilities_rtree'");
  print("R-Tree schema: ${schemaResult.first['sql']}");
  
  // Check indexes
  final indexes = db.select("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL");
  for (final row in indexes) {
    print("INDEX: ${row['name']} -> ${row['sql']}");
  }
  
  // Count rows in bounding box - current query (wrong - uses >= on min_lat and <= on max_lat)
  final current = db.select("""
    SELECT COUNT(*) as c FROM facilities_rtree r
    JOIN facilities f ON f.id = r.id
    WHERE r.min_lat >= 36.7488 AND r.max_lat <= 36.7588
      AND r.min_lon >= 3.0538 AND r.max_lon <= 3.0638
  """);
  print("Current query rows: ${current.first['c']}");
  
  // Correct R-Tree usage (overlap test)
  final corrected = db.select("""
    SELECT COUNT(*) as c FROM facilities_rtree r
    JOIN facilities f ON f.id = r.id
    WHERE r.min_lat <= 36.7588 AND r.max_lat >= 36.7488
      AND r.min_lon <= 3.0638 AND r.max_lon >= 3.0538
  """);
  print("Corrected query rows: ${corrected.first['c']}");
  
  // EXPLAIN QUERY PLAN - current
  print("\n--- Current query plan ---");
  final plan1 = db.select("EXPLAIN QUERY PLAN SELECT 1 FROM facilities_rtree r JOIN facilities f ON f.id = r.id WHERE r.min_lat >= 36.7488 AND r.max_lat <= 36.7588 AND r.min_lon >= 3.0538 AND r.max_lon <= 3.0638");
  for (final row in plan1) { print(row); }
  
  // EXPLAIN QUERY PLAN - corrected
  print("\n--- Corrected query plan ---");
  final plan2 = db.select("EXPLAIN QUERY PLAN SELECT 1 FROM facilities_rtree r JOIN facilities f ON f.id = r.id WHERE r.min_lat <= 36.7588 AND r.max_lat >= 36.7488 AND r.min_lon <= 3.0638 AND r.max_lon >= 3.0538");
  for (final row in plan2) { print(row); }
  
  db.dispose();
}
