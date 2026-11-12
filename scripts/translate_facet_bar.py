with open('lib/features/map/widgets/facet_filter_bar.dart', 'r', encoding='utf-8') as f:
    c = f.read()

import_line = "import '../../../core/services/medizy_locale.dart';\n"
if 'medizy_locale.dart' not in c:
    c = import_line + c

c = c.replace("'Rechercher médecin, pharmacie, commune...'", "MedizyLocale.t('Rechercher médecin, pharmacie, commune...', 'ابحث عن طبيب، صيدلية، بلدية...')")
c = c.replace("'Wilaya (58)'", "MedizyLocale.t('Wilaya (58)', 'الولاية (58)')")
c = c.replace("const Text('Urgences & Garde')", "Text(MedizyLocale.t('Urgences & Garde', 'استعجالات ومناوبات'))")
c = c.replace("const Text('Conventionné Chifa')", "Text(MedizyLocale.t('Conventionné Chifa', 'مؤمن بطاقة الشفاء'))")
c = c.replace("const Text('Mes favoris')", "Text(MedizyLocale.t('Mes favoris', 'مفضلاتي'))")
c = c.replace("const Text('Réinitialiser'", "Text(MedizyLocale.t('Réinitialiser', 'إعادة تعيين')")

with open('lib/features/map/widgets/facet_filter_bar.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated facet_filter_bar.dart with MedizyLocale')

