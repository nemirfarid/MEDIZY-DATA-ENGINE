import re

with open('lib/core/services/offline_health_search_service.dart', 'r', encoding='utf-8') as f:
    text = f.read()

# Pattern to find appendCategoryClause implementation
pattern = r'  static void appendCategoryClause\([^\{]+\{.*?\n  \}'

new_method = """  static void appendCategoryClause(
    StringBuffer sb,
    List<dynamic> params,
    String category, {
    String col = 'f.categorie',
    String? nomCol = 'f.nom',
  }) {
    final cat = category.trim().toLowerCase();
    final nc = nomCol ?? col;

    if (cat.contains('dentist') || cat.contains('dentaire') || cat.contains('stomatolog')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%dentist%', '%dentaire%', '%dentist%', '%dentaire%']);
    } else if (cat.contains('pharmac') || cat.contains('officine')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%pharmac%', '%officine%', '%pharmac%']);
    } else if (cat.contains('laboratoire') || cat.contains('analyse') || cat.contains('biolog')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%laboratoire%', '%analyse%', '%laboratoire%', '%analyse%']);
    } else if (cat.contains('imagerie') || cat.contains('radio') || cat.contains('scanner') || cat.contains('irm')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%imagerie%', '%radio%', '%scanner%', '%imagerie%', '%radio%']);
    } else if (cat.contains('pédiatr') || cat.contains('pediatr') || cat.contains('enfant')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%pediatr%', '%pédiatr%', '%pediatr%', '%pédiatr%']);
    } else if (cat.contains('cardio') || cat.contains('coeur')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%cardio%', '%cardio%']);
    } else if (cat.contains('ophtalmo') || cat.contains('yeux') || cat.contains('vision')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%ophtalm%', '%opticien%', '%ophtalm%']);
    } else if (cat.contains('gynéco') || cat.contains('gyneco') || cat.contains('matern')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%gyneco%', '%gynéco%', '%matern%', '%gyneco%', '%gynéco%']);
    } else if (cat.contains('dermat')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%dermat%', '%dermat%']);
    } else if (cat.contains('orthopéd') || cat.contains('orthoped')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%orthoped%', '%orthopéd%', '%orthoped%', '%orthopéd%']);
    } else if (cat.contains('gastro')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%gastro%', '%gastro%']);
    } else if (cat.contains('pneumo')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%pneumo%', '%pneumo%']);
    } else if (cat.contains('orl') || cat.contains('rhino')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%orl%', '%rhino%', '%orl%', '%rhino%']);
    } else if (cat.contains('psych')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%psych%', '%psych%']);
    } else if (cat.contains('kiné') || cat.contains('kine') || cat.contains('paraméd') || cat.contains('paramed') || cat.contains('physio')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%kine%', '%kiné%', '%paramed%', '%kine%', '%kiné%']);
    } else if (cat.contains('clinique') || cat.contains('hopital') || cat.contains('hôpital') || cat.contains('chu') || cat.contains('eph')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%clinique%', '%hopital%', '%hôpital%', '%clinique%', '%hopital%']);
    } else if (cat.contains('urgenc') || cat.contains('garde') || cat.contains('24/24')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%urgence%', '%urgenc%', '%garde%', '%24/24%']);
    } else if (cat.contains('généralist') || cat.contains('generalist') || cat.contains('medecin') || cat.contains('médecin')) {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($col) LIKE ? OR LOWER($col) = ? OR LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%generalist%', '%généralist%', 'medecin', '%cabinet medical%', '%généraliste%']);
    } else {
      sb.writeln('  AND (LOWER($col) LIKE ? OR LOWER($nc) LIKE ?)');
      params.addAll(['%$cat%', '%$cat%']);
    }
  }"""

updated, count = re.subn(pattern, new_method, text, flags=re.DOTALL)
print("Replaced count:", count)
if count > 0:
    with open('lib/core/services/offline_health_search_service.dart', 'w', encoding='utf-8') as f:
        f.write(updated)
    print("Updated offline_health_search_service.dart!")

