with open('lib/features/home/presentation/widgets/category_grid.dart', 'r', encoding='utf-8') as f:
    c = f.read()

import_line = "import '../../../../core/services/medizy_locale.dart';\n"
if 'medizy_locale.dart' not in c:
    c = import_line + c

# Replace label in _CategoryItemCard call
c = c.replace("label: cat['label'] as String,", "label: MedizyLocale.translateCategory(cat['label'] as String),")

with open('lib/features/home/presentation/widgets/category_grid.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated category_grid.dart with MedizyLocale translation!')

