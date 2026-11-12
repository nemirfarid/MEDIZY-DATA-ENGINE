with open('lib/features/map/widgets/wilaya_picker_sheet.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace 'const Text(MedizyLocale.t' with 'Text(MedizyLocale.t'
c = c.replace("const Text(MedizyLocale.t", "Text(MedizyLocale.t")
c = c.replace("const Text(\n                    MedizyLocale.t", "Text(\n                    MedizyLocale.t")
c = c.replace("const Text(\n                      MedizyLocale.t", "Text(\n                      MedizyLocale.t")

with open('lib/features/map/widgets/wilaya_picker_sheet.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Fixed const in wilaya_picker_sheet.dart')

