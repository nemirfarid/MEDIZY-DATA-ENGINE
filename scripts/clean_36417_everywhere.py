with open('lib/features/map/widgets/wilaya_picker_sheet.dart', 'r', encoding='utf-8') as f:
    c = f.read()

import_line = "import '../../../core/services/medizy_locale.dart';\n"
if 'medizy_locale.dart' not in c:
    c = import_line + c

c = c.replace("'Toute l\\'Algérie (36 417 fiches)'", "MedizyLocale.t('Toute l\\'Algérie (59 658 fiches)', 'كامل الجزائر (59 658 هيكل صحي)')")
c = c.replace("'Sélectionner une Wilaya'", "MedizyLocale.t('Sélectionner une Wilaya', 'اختر ولاية')")
c = c.replace("'Rechercher une wilaya...'", "MedizyLocale.t('Rechercher une wilaya...', 'ابحث عن ولاية...')")

with open('lib/features/map/widgets/wilaya_picker_sheet.dart', 'w', encoding='utf-8') as f:
    f.write(c)

# Clean offline_map_view.dart of 36 417
with open('lib/features/map/offline_map_view.dart', 'r', encoding='utf-8') as f:
    c2 = f.read()

c2 = c2.replace("'Toute l\\'Algérie (36 417 fiches)'", "MedizyLocale.t('Toute l\\'Algérie (59 658 fiches)', 'كامل الجزائر (59 658 هيكل صحي)')")
c2 = c2.replace("Toute l'Algérie (36 417 fiches)", "Toute l'Algérie (59 658 fiches)")

with open('lib/features/map/offline_map_view.dart', 'w', encoding='utf-8') as f:
    f.write(c2)

print('Cleaned 36417 and updated wilaya picker & offline map view!')

