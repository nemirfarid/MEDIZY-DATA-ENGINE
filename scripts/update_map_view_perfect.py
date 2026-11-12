with open('lib/features/map/offline_map_view.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Remplacer '36417' par '59 658'
c = c.replace('36417', '59658')

# 2. Modifier _loadViewport pour charger tous les établissements du rectangle visible (jusqu'à 1500 au lieu de 150)
c = c.replace('limit: 150,', 'limit: 1500,')
c = c.replace('limit: 150', 'limit: 1500')

# 3. Ajouter l'écoute du mouvement de la carte (onPositionChanged) pour recharger automatiquement le viewport
# quand on navigue ou qu'on se déplace sur une autre commune
map_options_old = '''            options: MapOptions(
              initialCenter: widget.initialCenter,
              initialZoom: widget.initialZoom,
              minZoom: 4.5,
              maxZoom: 18.0,
              backgroundColor: const Color(0xFFEFF3F4), // Fond neutre clair médical hors-ligne
            ),'''

map_options_new = '''            options: MapOptions(
              initialCenter: widget.initialCenter,
              initialZoom: widget.initialZoom,
              minZoom: 4.5,
              maxZoom: 18.0,
              backgroundColor: const Color(0xFFEFF3F4),
              onPositionChanged: (camera, hasGesture) {
                // Dès que l'utilisateur déplace la carte sur une autre commune ou zoome
                if (camera.zoom >= 11.0) {
                  _loadViewport();
                }
              },
            ),'''

c = c.replace(map_options_old, map_options_new)

# 4. Déplacer le bouton SOS Santé 24/7 en haut à droite sous la barre d'outils au lieu de masquer le bas de la carte
sos_old = '''          // 5. Bouton d'Urgence Immédiate "SOS Santé 24/7" (Toujours accessible en bas à gauche)
          Positioned(
            bottom: 24,
            left: 16,
            child: SosEmergencyButton(
              searchService: widget.searchService,
              userPosition: _userPosition,
            ),
          ),'''

sos_new = '''          // 5. Bouton d'Urgence Immédiate "SOS Santé 24/7" repositionné proprement
          Positioned(
            bottom: 24,
            right: 76,
            child: SosEmergencyButton(
              searchService: widget.searchService,
              userPosition: _userPosition,
            ),
          ),'''

c = c.replace(sos_old, sos_new)

# 5. Localisation arabe de la barre de titre et sous-titres
c = c.replace("'Sélecteur de Wilaya (58)'", "MedizyLocale.t('Sélecteur de Wilaya (58)', 'اختيار الولاية (58)')")
c = c.replace("'Toutes communes'", "MedizyLocale.t('Toutes communes', 'كل البلديات')")
c = c.replace("'fiches • 58 Wilayas'", "MedizyLocale.t('fiches • 58 Wilayas', 'هيكل صحي • 58 ولاية')")

with open('lib/features/map/offline_map_view.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Updated offline_map_view.dart successfully with viewport reloading, 59658 count, relocated SOS and Arabic translations')

