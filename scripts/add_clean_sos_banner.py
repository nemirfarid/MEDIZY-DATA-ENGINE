with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Add SOS banner right below the header Container in Column children
sos_banner = '''            // 1.5. Bouton d'urgence SOS Santé 24/7 intégré dans la bannière supérieure (non flottant)
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              width: double.infinity,
              height: 44,
              child: ElevatedButton.icon(
                key: const Key('home_sos_banner_button'),
                icon: const Icon(Icons.emergency_rounded, color: Colors.white, size: 22),
                label: Text(
                  MedizyLocale.t('SOS Urgences Santé 24/7 (Samu 14 • Protection Civile 1021)', 'طوارئ صحية 24/7 (إسعاف 14 • حماية مدنية 1021)'),
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                  overflow: TextOverflow.ellipsis,
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFC62828),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 2,
                ),
                onPressed: () {
                  SosEmergencyButton(searchService: widget.searchService).build(context);
                },
              ),
            ),
'''

target = '            // Grille épurée de catégories (responsive 3 ou 4 colonnes)'
if 'home_sos_banner_button' not in c:
    c = c.replace(target, sos_banner + target)
    with open('lib/features/home/presentation/screens/medizy_home_screen.dart', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Added clean SOS banner to home screen')

