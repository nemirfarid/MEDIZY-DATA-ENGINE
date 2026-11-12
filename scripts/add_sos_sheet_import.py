with open('lib/features/map/offline_map_view.dart', 'r', encoding='utf-8') as f:
    c = f.read()

import_sheet = "import '../emergency/presentation/widgets/sos_emergency_sheet.dart';\n"
if 'sos_emergency_sheet.dart' not in c:
    c = import_sheet + c
    with open('lib/features/map/offline_map_view.dart', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Added sos_emergency_sheet.dart import to offline_map_view.dart')
else:
    print('Already present')

