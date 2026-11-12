with open('lib/features/map/offline_map_view.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Add Communes Chip Bar underneath the top facet bar
commune_bar = '''          // 2.2. Barre déroulante des Communes (lorsqu'une Wilaya est sélectionnée)
          if (_selectedWilayaCode != null && _availableCommunes.isNotEmpty)
            Positioned(
              top: 104,
              left: 12,
              right: 12,
              child: Container(
                height: 42,
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.12),
                      blurRadius: 6,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  physics: const BouncingScrollPhysics(),
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        label: const Text('Toutes communes', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        selected: _selectedCommune == null,
                        selectedColor: Colors.teal.shade800,
                        labelStyle: TextStyle(
                          color: _selectedCommune == null ? Colors.white : Colors.teal.shade900,
                        ),
                        onSelected: (selected) {
                          if (selected) {
                            setState(() => _selectedCommune = null);
                            _applyFilters();
                          }
                        },
                      ),
                    ),
                    ..._availableCommunes.map((com) {
                      final isSelected = _selectedCommune == com;
                      return Padding(
                        padding: const EdgeInsets.only(right: 6),
                        child: ChoiceChip(
                          label: Text(com, style: const TextStyle(fontSize: 12)),
                          selected: isSelected,
                          selectedColor: Colors.teal.shade700,
                          labelStyle: TextStyle(
                            color: isSelected ? Colors.white : Colors.grey.shade800,
                            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          ),
                          onSelected: (selected) {
                            setState(() => _selectedCommune = selected ? com : null);
                            _applyFilters();
                            if (selected && _displayedFacilities.isNotEmpty) {
                              final f = _displayedFacilities.first;
                              _mapController.move(LatLng(f.latitude, f.longitude), 13.5);
                            }
                          },
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),
            ),
'''

target = '          // 2.5. Badge actif et dismissible de catégorie sélectionnée'
if '2.2. Barre déroulante des Communes' not in c:
    c = c.replace(target, commune_bar + '\n' + target)
    with open('lib/features/map/offline_map_view.dart', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Added commune chips bar to offline_map_view.dart')
else:
    print('Commune bar already exists')

