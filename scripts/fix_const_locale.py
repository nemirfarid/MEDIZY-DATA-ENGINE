with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace any 'const Text(\n                          MedizyLocale.t' with 'Text(\n                          MedizyLocale.t'
c = c.replace("const Text(\n                          MedizyLocale.t", "Text(\n                          MedizyLocale.t")
c = c.replace("const Text(\n                    MedizyLocale.t", "Text(\n                    MedizyLocale.t")

with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Successfully removed invalid const from MedizyHomeScreen')

