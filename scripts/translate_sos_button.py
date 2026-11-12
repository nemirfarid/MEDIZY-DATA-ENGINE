with open('lib/features/emergency/presentation/widgets/sos_emergency_button.dart', 'r', encoding='utf-8') as f:
    c = f.read()

import_line = "import '../../../../core/services/medizy_locale.dart';\n"
if 'medizy_locale.dart' not in c:
    c = import_line + c

c = c.replace("const Text(\n          'SOS Santé 24/7',", "Text(\n          MedizyLocale.t('SOS Santé 24/7', 'طوارئ صحية 24/7'),")

with open('lib/features/emergency/presentation/widgets/sos_emergency_button.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated sos_emergency_button.dart with Arabic translation')

