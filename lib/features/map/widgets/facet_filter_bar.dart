import 'package:flutter/material.dart';

/// Barre de filtrage par facettes (Wilaya, Spécialité, Statut d'urgence, Conventionné Chifa)
class FacetFilterBar extends StatelessWidget {
  final String? selectedWilayaCode;
  final String? selectedWilayaName;
  final String? selectedCategory;
  final bool onlyEmergency;
  final bool showChifa;
  final ValueChanged<String?> onWilayaChanged;
  final VoidCallback? onWilayaPickerRequested;
  final ValueChanged<String?> onCategoryChanged;
  final ValueChanged<bool> onEmergencyToggled;
  final ValueChanged<bool> onChifaToggled;
  final ValueChanged<String> onSearchSubmitted;

  const FacetFilterBar({
    Key? key,
    this.selectedWilayaCode,
    this.selectedWilayaName,
    this.selectedCategory,
    required this.onlyEmergency,
    required this.showChifa,
    required this.onWilayaChanged,
    this.onWilayaPickerRequested,
    required this.onCategoryChanged,
    required this.onEmergencyToggled,
    required this.onChifaToggled,
    required this.onSearchSubmitted,
  }) : super(key: key);

  static const List<Map<String, String>> topCategories = [
    {'code': '', 'label': 'Toutes catégories'},
    {'code': 'Pharmacie', 'label': 'Pharmacies'},
    {'code': 'Médecin Généraliste', 'label': 'Généralistes'},
    {'code': 'Hôpital', 'label': 'Hôpitaux & Cliniques'},
    {'code': 'Laboratoire d\'analyses', 'label': 'Laboratoires'},
    {'code': 'Dentiste', 'label': 'Dentistes'},
    {'code': 'Cardiologue', 'label': 'Cardiologues'},
    {'code': 'Pédiatre', 'label': 'Pédiatres'},
    {'code': 'Gynécologue', 'label': 'Gynécologues'},
    {'code': 'Ophtalmologue', 'label': 'Ophtalmologues'},
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: theme.cardColor.withOpacity(0.96),
        boxShadow: const [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Ligne 1 : Champ de recherche FTS5
          TextField(
            decoration: InputDecoration(
              hintText: 'Rechercher médecin, pharmacie, commune...',
              prefixIcon: const Icon(Icons.search, color: Colors.teal),
              suffixIcon: IconButton(
                icon: const Icon(Icons.clear, size: 18),
                onPressed: () => onSearchSubmitted(''),
              ),
              isDense: true,
              filled: true,
              fillColor: Colors.grey.shade100,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide.none,
              ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            ),
            onSubmitted: onSearchSubmitted,
          ),
          const SizedBox(height: 8),

          // Ligne 2 : Filtres rapides Wilaya (58), Catégorie, Urgence
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                // Sélecteur explicite Wilaya (58 Wilayas)
                FilterChip(
                  avatar: Icon(
                    Icons.location_city,
                    size: 15,
                    color: selectedWilayaCode != null ? Colors.white : Colors.teal.shade800,
                  ),
                  label: Text(
                    selectedWilayaCode != null
                        ? '$selectedWilayaCode ${selectedWilayaName ?? ""}'
                        : 'Wilaya (58)',
                  ),
                  selected: selectedWilayaCode != null,
                  selectedColor: Colors.teal.shade800,
                  labelStyle: TextStyle(
                    color: selectedWilayaCode != null ? Colors.white : Colors.teal.shade900,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                  onSelected: (_) => onWilayaPickerRequested?.call(),
                ),
                const SizedBox(width: 8),

                // Bouton filtre Urgence / 24h
                FilterChip(
                  avatar: Icon(
                    Icons.emergency,
                    size: 16,
                    color: onlyEmergency ? Colors.white : Colors.red,
                  ),
                  label: const Text('Urgences & Garde'),
                  selected: onlyEmergency,
                  selectedColor: Colors.red.shade700,
                  labelStyle: TextStyle(
                    color: onlyEmergency ? Colors.white : Colors.red.shade900,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                  onSelected: onEmergencyToggled,
                ),
                const SizedBox(width: 8),

                // Bouton Conventionné Chifa
                FilterChip(
                  avatar: Icon(
                    Icons.health_and_safety,
                    size: 16,
                    color: showChifa ? Colors.white : Colors.orange.shade700,
                  ),
                  label: const Text('Conventionné Chifa'),
                  selected: showChifa,
                  selectedColor: Colors.orange.shade700,
                  labelStyle: TextStyle(
                    color: showChifa ? Colors.white : Colors.orange.shade900,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                  onSelected: onChifaToggled,
                ),
                const SizedBox(width: 8),

                // Sélecteur Catégorie
                DropdownButtonHideUnderline(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                    decoration: BoxDecoration(
                      color: selectedCategory != null ? Colors.teal.shade50 : Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: selectedCategory != null ? Colors.teal.shade300 : Colors.grey.shade300,
                      ),
                    ),
                    child: DropdownButton<String>(
                      value: selectedCategory ?? '',
                      isDense: true,
                      style: TextStyle(
                        color: selectedCategory != null ? Colors.teal.shade900 : Colors.black87,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                      items: topCategories.map((c) {
                        return DropdownMenuItem<String>(
                          value: c['code'],
                          child: Text(c['label']!),
                        );
                      }).toList(),
                      onChanged: (val) {
                        onCategoryChanged(val == null || val.isEmpty ? null : val);
                      },
                    ),
                  ),
                ),
                const SizedBox(width: 8),

                // Bouton Réinitialiser si des filtres sont actifs
                if (selectedWilayaCode != null || selectedCategory != null || onlyEmergency || showChifa)
                  ActionChip(
                    avatar: const Icon(Icons.refresh, size: 14),
                    label: const Text('Réinitialiser', style: TextStyle(fontSize: 11)),
                    onPressed: () {
                      onWilayaChanged(null);
                      onCategoryChanged(null);
                      onEmergencyToggled(false);
                      onChifaToggled(false);
                      onSearchSubmitted('');
                    },
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
