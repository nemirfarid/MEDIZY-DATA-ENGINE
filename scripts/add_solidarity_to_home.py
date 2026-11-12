with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'r', encoding='utf-8') as f:
    content = f.read()

import_line = "import '../../../pharma/presentation/widgets/solidarity_sheet.dart';\n"
if 'solidarity_sheet.dart' not in content:
    content = import_line + content

solidarity_btn = """          IconButton(
            key: const Key('home_solidarity_button'),
            icon: const Icon(Icons.volunteer_activism_rounded),
            tooltip: 'Wasfa Tikafol (Solidarite & Entraide)',
            onPressed: () {
              SolidaritySheet.show(context);
            },
          ),
"""

if 'home_solidarity_button' not in content:
    idx = content.find('actions: [')
    if idx != -1:
        insert_pos = idx + len('actions: [\n')
        content = content[:insert_pos] + solidarity_btn + content[insert_pos:]

with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'w', encoding='utf-8') as f:
    f.write(content)

print('Success adding solidarity button to MedizyHomeScreen')

