with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'r', encoding='utf-8') as f:
    c = f.read()

import_sheet = "import '../../../emergency/presentation/widgets/sos_emergency_sheet.dart';\n"
if 'sos_emergency_sheet.dart' not in c:
    c = import_sheet + c

old_call = "SosEmergencyButton(searchService: widget.searchService).build(context);"
new_call = "SosEmergencySheet.show(context, searchService: widget.searchService);"
c = c.replace(old_call, new_call)

with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated SOS sheet call in home screen banner!')

