import '../../../core/services/medizy_locale.dart';
import 'package:flutter/material.dart';

/// Barre de filtrage ordonnée sur la carte :
/// 1. Bouton Wilaya (en haut à gauche)
/// 2. Bouton Communes adéquates à la Wilaya sélectionnée
/// 3. Bouton Choix des Catégories
/// 4. Reste des boutons (Urgences, Chifa, Favoris, Réinitialiser)
///
/// Comportement "Près de moi" :
/// Lorsque le mode "Près de moi" est actif (isNearMeActive = true), les boutons Wilaya et Commune
/// sont désactivés, tandis que le bouton Catégorie reste actif pour filtrer autour de soi.
class FacetFilterBar extends StatelessWidget {
  final String? selectedWilayaCode;
  final String? selectedWilayaName;
  final String? selectedCommune;
  final List<String> availableCommunes;
  final String? selectedCategory;
  final bool onlyEmergency;
  final bool showChifa;
  final bool showFavorites;
  final bool isNearMeActive;

  final ValueChanged<String?> onWilayaChanged;
  final VoidCallback? onWilayaPickerRequested;
  final ValueChanged<String?> onCommuneChanged;
  final ValueChanged<String?> onCategoryChanged;
  final ValueChanged<bool> onEmergencyToggled;
  final ValueChanged<bool> onChifaToggled;
  final ValueChanged<bool> onFavoritesToggled;
  final ValueChanged<String> onSearchSubmitted;

  const FacetFilterBar({
    Key? key,
    this.selectedWilayaCode,
    this.selectedWilayaName,
    this.selectedCommune,
    this.availableCommunes = const [],
    this.selectedCategory,
    required this.onlyEmergency,
    required this.showChifa,
    required this.showFavorites,
    this.isNearMeActive = false,
    required this.onWilayaChanged,
    this.onWilayaPickerRequested,
    required this.onCommuneChanged,
    required this.onCategoryChanged,
    required this.onEmergencyToggled,
    required this.onChifaToggled,
    required this.onFavoritesToggled,
    required this.onSearchSubmitted,
  }) : super(key: key);

  static const List<Map<String, dynamic>> topCategories = [
    {'code': '', 'label': 'Toutes catégories', 'icon': Icons.local_hospital_outlined},
    {'code': 'généraliste', 'label': 'Généralistes', 'icon': Icons.medical_services_rounded},
    {'code': 'dentiste', 'label': 'Dentistes', 'icon': Icons.sentiment_very_satisfied_rounded},
    {'code': 'pédiatre', 'label': 'Pédiatres', 'icon': Icons.child_care_rounded},
    {'code': 'pharmacie', 'label': 'Pharmacies', 'icon': Icons.medication_rounded},
    {'code': 'clinique', 'label': 'Cliniques & Hôpitaux', 'icon': Icons.domain_rounded},
    {'code': 'laboratoire', 'label': 'Laboratoires', 'icon': Icons.science_rounded},
    {'code': 'cardiologue', 'label': 'Cardiologues', 'icon': Icons.favorite_rounded},
    {'code': 'imagerie', 'label': 'Imagerie & Radiologie', 'icon': Icons.scanner_rounded},
    {'code': 'ophtalmologue', 'label': 'Ophtalmologues', 'icon': Icons.visibility_rounded},
    {'code': 'gynécologue', 'label': 'Gynécologues', 'icon': Icons.female_rounded},
    {'code': 'dermatologue', 'label': 'Dermatologues', 'icon': Icons.face_retouching_natural_rounded},
    {'code': 'urgences', 'label': 'Urgences 24/7', 'icon': Icons.emergency_rounded},
  ];

  void _showCommunePicker(BuildContext context) {
    if (availableCommunes.isEmpty) return;

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        String filter = '';
        return StatefulBuilder(
          builder: (context, setModalState) {
            final filtered = availableCommunes.where((c) {
              return filter.isEmpty || c.toLowerCase().contains(filter.toLowerCase());
            }).toList();

            return Container(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              height: MediaQuery.of(context).size.height * 0.65,
              child: Column(
                children: [
                  Container(
                    width: 40,
                    height: 4,
                    margin: EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Communes ($selectedWilayaName)',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      if (selectedCommune != null)
                        TextButton(
                          onPressed: () {
                            onCommuneChanged(null);
                            Navigator.pop(ctx);
                          },
                          child: const Text('Toutes', style: TextStyle(color: Colors.red)),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    decoration: InputDecoration(
                      hintText: 'Rechercher une commune...',
                      prefixIcon: const Icon(Icons.search, size: 20),
                      isDense: true,
                      filled: true,
                      fillColor: Colors.grey.shade100,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                    ),
                    onChanged: (val) => setModalState(() => filter = val),
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: ListView.separated(
                      itemCount: filtered.length + 1,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        if (index == 0) {
                          final isSelected = selectedCommune == null;
                          return ListTile(
                            title: const Text('Toutes les communes (Toute la wilaya)'),
                            trailing: isSelected ? const Icon(Icons.check, color: Colors.teal) : null,
                            onTap: () {
                              onCommuneChanged(null);
                              Navigator.pop(ctx);
                            },
                          );
                        }
                        final com = filtered[index - 1];
                        final isSelected = selectedCommune == com;
                        return ListTile(
                          title: Text(com),
                          trailing: isSelected ? const Icon(Icons.check, color: Colors.teal) : null,
                          onTap: () {
                            onCommuneChanged(com);
                            Navigator.pop(ctx);
                          },
                        );
                      },
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _showCategoryPicker(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Container(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 40,
                height: 4,
                margin: EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const Text(
                'Choisir une spécialité de santé',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: topCategories.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final item = topCategories[index];
                    final code = item['code'] as String;
                    final label = item['label'] as String;
                    final icon = item['icon'] as IconData;
                    final isSelected = (selectedCategory ?? '') == code;

                    return ListTile(
                      leading: Icon(icon, color: Colors.teal.shade800),
                      title: Text(
                        label,
                        style: TextStyle(
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          color: isSelected ? Colors.teal.shade900 : Colors.black87,
                        ),
                      ),
                      trailing: isSelected ? const Icon(Icons.check, color: Colors.teal) : null,
                      onTap: () {
                        onCategoryChanged(code.isEmpty ? null : code);
                        Navigator.pop(ctx);
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

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
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Ligne 1 : Champ de recherche FTS5
          TextField(
            decoration: InputDecoration(
              hintText: MedizyLocale.t('Rechercher médecin, pharmacie, commune...', 'ابحث عن طبيب، صيدلية، بلدية...'),
              prefixIcon: const Icon(Icons.search, color: Colors.teal),
              suffixIcon: IconButton(
                icon: const Icon(Icons.backspace_outlined, size: 18),
                onPressed: () => onSearchSubmitted(''),
              ),
              isDense: true,
              filled: true,
              fillColor: Colors.grey.shade100,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(16),
                borderSide: BorderSide.none,
              ),
              contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            ),
            onSubmitted: onSearchSubmitted,
          ),
          const SizedBox(height: 8),

          // Ligne 2 : Filtres organisés selon l'ordre strict demandé :
          // 1. Bouton Wilaya (en haut à gauche)
          // 2. Bouton Communes adéquates à la Wilaya
          // 3. Bouton Choix des Catégories
          // 4. Reste des boutons (Urgences, Chifa, Favoris, Réinitialiser)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                // 1. BOUTON 1 : WILAYA (En premier à gauche)
                Opacity(
                  opacity: isNearMeActive ? 0.45 : 1.0,
                  child: FilterChip(
                    avatar: Icon(
                      Icons.location_city,
                      size: 15,
                      color: selectedWilayaCode != null ? Colors.white : Colors.teal.shade800,
                    ),
                    label: Text(
                      selectedWilayaCode != null
                          ? '$selectedWilayaCode ${selectedWilayaName ?? ""}'
                          : MedizyLocale.t('Wilaya (58)', 'الولاية (58)'),
                    ),
                    selected: selectedWilayaCode != null,
                    selectedColor: Colors.teal.shade800,
                    labelStyle: TextStyle(
                      color: selectedWilayaCode != null ? Colors.white : Colors.teal.shade900,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                    onSelected: isNearMeActive ? null : (_) => onWilayaPickerRequested?.call(),
                  ),
                ),
                const SizedBox(width: 8),

                // 2. BOUTON 2 : COMMUNES (Juste après la Wilaya)
                Opacity(
                  opacity: isNearMeActive ? 0.45 : 1.0,
                  child: FilterChip(
                    avatar: Icon(
                      Icons.map_outlined,
                      size: 15,
                      color: selectedCommune != null ? Colors.white : Colors.teal.shade800,
                    ),
                    label: Text(
                      selectedCommune != null
                          ? selectedCommune!
                          : (selectedWilayaCode != null && availableCommunes.isNotEmpty)
                              ? 'Commune (${availableCommunes.length})'
                              : MedizyLocale.t('Commune', 'البلدية'),
                    ),
                    selected: selectedCommune != null,
                    selectedColor: Colors.teal.shade700,
                    labelStyle: TextStyle(
                      color: selectedCommune != null ? Colors.white : Colors.teal.shade900,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                    onSelected: (isNearMeActive || selectedWilayaCode == null || availableCommunes.isEmpty)
                        ? null
                        : (_) => _showCommunePicker(context),
                  ),
                ),
                const SizedBox(width: 8),

                // 3. BOUTON 3 : CATÉGORIES (Reste toujours actif même en mode "Près de moi")
                FilterChip(
                  avatar: Icon(
                    selectedCategory != null ? Icons.check_circle : Icons.category_rounded,
                    size: 15,
                    color: selectedCategory != null ? Colors.white : Colors.teal.shade800,
                  ),
                  label: Text(
                    selectedCategory != null
                        ? (selectedCategory![0].toUpperCase() + selectedCategory!.substring(1))
                        : MedizyLocale.t('Catégorie', 'التخصص / الفئة'),
                  ),
                  selected: selectedCategory != null,
                  selectedColor: Colors.teal.shade900,
                  labelStyle: TextStyle(
                    color: selectedCategory != null ? Colors.white : Colors.teal.shade900,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                  onSelected: (_) => _showCategoryPicker(context),
                ),
                const SizedBox(width: 8),

                // 4. BOUTON 4 : Urgences / Garde 24h
                FilterChip(
                  avatar: Icon(
                    Icons.emergency,
                    size: 16,
                    color: onlyEmergency ? Colors.white : Colors.red,
                  ),
                  label: Text(MedizyLocale.t('Urgences & Garde', 'استعجالات ومناوبات')),
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

                // 5. BOUTON 5 : Conventionné Chifa
                FilterChip(
                  avatar: Icon(
                    Icons.health_and_safety,
                    size: 16,
                    color: showChifa ? Colors.white : Colors.orange.shade700,
                  ),
                  label: Text(MedizyLocale.t('Conventionné Chifa', 'مؤمن بطاقة الشفاء')),
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

                // 6. BOUTON 6 : Favoris
                FilterChip(
                  avatar: Icon(
                    Icons.star,
                    size: 16,
                    color: showFavorites ? Colors.white : Colors.amber.shade700,
                  ),
                  label: Text(MedizyLocale.t('Mes favoris', 'مفضلاتي')),
                  selected: showFavorites,
                  selectedColor: Colors.amber.shade700,
                  labelStyle: TextStyle(
                    color: showFavorites ? Colors.white : Colors.amber.shade900,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                  onSelected: onFavoritesToggled,
                ),
                const SizedBox(width: 8),

                // 7. BOUTON 7 : Réinitialiser si des filtres sont actifs
                if (selectedWilayaCode != null || selectedCommune != null || selectedCategory != null || onlyEmergency || showChifa || showFavorites)
                  ActionChip(
                    avatar: const Icon(Icons.refresh, size: 14),
                    label: Text(MedizyLocale.t('Réinitialiser', 'إعادة تعيين'), style: const TextStyle(fontSize: 11)),
                    onPressed: () {
                      onWilayaChanged(null);
                      onCommuneChanged(null);
                      onCategoryChanged(null);
                      onEmergencyToggled(false);
                      onChifaToggled(false);
                      onFavoritesToggled(false);
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
