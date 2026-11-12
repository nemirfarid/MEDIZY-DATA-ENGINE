with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace("import '../../../emergency/presentation/widgets/sos_emergency_button.dart';\n", "")

with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'w', encoding='utf-8') as f:
    f.write(c)

with open('lib/features/map/offline_map_view.dart', 'r', encoding='utf-8') as f:
    c2 = f.read()

c2 = c2.replace("import '../emergency/presentation/widgets/sos_emergency_button.dart';\n", "")

with open('lib/features/map/offline_map_view.dart', 'w', encoding='utf-8') as f:
    f.write(c2)

print('Cleaned unused imports')

