with open('lib/features/map/offline_map_view.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Add SOS action button in AppBar
sos_action = """          IconButton(
            icon: const Icon(Icons.emergency_rounded, color: Colors.amberAccent),
            tooltip: MedizyLocale.t('SOS Urgences 24/7', 'طوارئ صحية 24/7'),
            onPressed: () {
              SosEmergencySheet.show(context, searchService: widget.searchService, userPosition: _userPosition);
            },
          ),
"""

if "tooltip: MedizyLocale.t('SOS Urgences 24/7'" not in c:
    target = '          // Bouton sélecteur de Wilaya'
    c = c.replace(target, sos_action + target)

# Remove the floating Positioned SOS button at bottom
old_positioned_sos = """          // 5. Bouton d'Urgence Immédiate "SOS Santé 24/7" repositionné proprement
          Positioned(
            bottom: 24,
            right: 76,
            child: SosEmergencyButton(
              searchService: widget.searchService,
              userPosition: _userPosition,
            ),
          ),"""

c = c.replace(old_positioned_sos, "")

with open('lib/features/map/offline_map_view.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Moved SOS button to map AppBar and completely removed bottom floating obstruction!')

