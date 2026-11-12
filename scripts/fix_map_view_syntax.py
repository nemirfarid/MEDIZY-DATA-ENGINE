with open('lib/features/map/offline_map_view.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Add import
import_line = "import '../../core/services/medizy_locale.dart';\n"
if 'medizy_locale.dart' not in c:
    c = import_line + c

# Fix null check on camera.zoom >= 11.0
c = c.replace('if (camera.zoom >= 11.0)', 'if ((camera.zoom ?? 11.0) >= 11.0)')

# Fix const Text containing MedizyLocale.t('Toutes communes'...)
c = c.replace("const Text(MedizyLocale.t('Toutes communes'", "Text(MedizyLocale.t('Toutes communes'")

with open('lib/features/map/offline_map_view.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Cleaned MedizyLocale import, null check and const Text in offline_map_view.dart')

