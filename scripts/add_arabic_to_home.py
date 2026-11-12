with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Add MedizyLocale import
if 'medizy_locale.dart' not in c:
    c = "import '../../../../core/services/medizy_locale.dart';\n" + c

# Add language toggle icon in AppBar actions
lang_btn = """          IconButton(
            key: const Key('home_language_toggle'),
            icon: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 1.2),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                MedizyLocale.isArabic ? 'FR' : 'عربي',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            tooltip: 'Changer la langue / تغيير اللغة',
            onPressed: () {
              setState(() {
                MedizyLocale.isArabic = !MedizyLocale.isArabic;
              });
            },
          ),
"""

if 'home_language_toggle' not in c:
    idx = c.find('actions: [')
    if idx != -1:
        insert_pos = idx + len('actions: [\n')
        c = c[:insert_pos] + lang_btn + c[insert_pos:]

# Update header text dynamically with MedizyLocale
c = c.replace("'Annuaire Sanitaire National'", "MedizyLocale.t('Annuaire Sanitaire National', 'الدليل الصحي الوطني')")
c = c.replace("'Sélectionnez une catégorie pour consulter la carte hors-ligne (58 Wilayas)'", "MedizyLocale.t('Sélectionnez une catégorie pour consulter la carte hors-ligne (58 Wilayas)', 'اختر تخصصاً لاستعراض الخريطة بدون إنترنت (58 ولاية)')")
c = c.replace("'Près de moi'", "MedizyLocale.t('Près de moi', 'بالقرب مني')")
c = c.replace("'Filtres (58)'", "MedizyLocale.t('Filtres (58)', 'فلترة (58 ولاية)')")

with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated MedizyHomeScreen with Arabic support and language switch')

