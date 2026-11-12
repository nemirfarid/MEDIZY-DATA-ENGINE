with open('lib/features/map/widgets/wilaya_picker_sheet.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace 'const Column(' with 'Column(' around line 62
c = c.replace("const Column(\n                  crossAxisAlignment: CrossAxisAlignment.start,", "Column(\n                  crossAxisAlignment: CrossAxisAlignment.start,")

with open('lib/features/map/widgets/wilaya_picker_sheet.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Successfully removed const Column in wilaya_picker_sheet.dart')

