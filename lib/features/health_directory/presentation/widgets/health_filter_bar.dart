import 'package:flutter/material.dart';
import '../../state/health_search_notifier.dart';

/// Barre de filtres ergonomique et réactive pour l'annuaire de santé
class HealthFilterBar extends StatelessWidget {
  final HealthSearchNotifier notifier;
  final bool isFavoritesOnly;
  final ValueChanged<bool>? onFavoritesOnlyChanged;

  const HealthFilterBar({
    super.key,
    required this.notifier,
    this.isFavoritesOnly = false,
    this.onFavoritesOnlyChanged,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: notifier,
      builder: (context, _) {
        final state = notifier.state;
        final selectedWilaya = state.filter.wilayaCode;
        final selectedCommune = state.filter.commune;
        final selectedSpecialty = state.filter.specialty;
        final isDutyActive = state.onlyOnDutyPharmacies;

        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              // 0. Filtre direct "Mes Favoris"
              if (onFavoritesOnlyChanged != null) ...[
                FilterChip(
                  key: const Key('favorites_filter_chip'),
                  selected: isFavoritesOnly,
                  avatar: Icon(
                    isFavoritesOnly ? Icons.star : Icons.star_border,
                    size: 16,
                    color: isFavoritesOnly ? Colors.white : Colors.amber.shade800,
                  ),
                  label: const Text('Mes Favoris', style: TextStyle(fontSize: 13)),
                  selectedColor: Colors.amber.shade800,
                  labelStyle: TextStyle(
                    color: isFavoritesOnly ? Colors.white : Colors.black87,
                    fontWeight: isFavoritesOnly ? FontWeight.bold : FontWeight.normal,
                  ),
                  checkmarkColor: Colors.white,
                  onSelected: onFavoritesOnlyChanged,
                ),
                const SizedBox(width: 8),
              ],

              // 1. Sélecteur des 58 Wilayas
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: selectedWilaya != null ? Colors.teal.shade700 : Colors.grey.shade300,
                    width: selectedWilaya != null ? 1.5 : 1.0,
                  ),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String?>(
                    key: const Key('wilaya_dropdown'),
                    value: selectedWilaya,
                    hint: const Text('Toutes les Wilayas', style: TextStyle(fontSize: 13)),
                    icon: const Icon(Icons.arrow_drop_down, size: 20),
                    isDense: true,
                    items: [
                      const DropdownMenuItem<String?>(
                        value: null,
                        child: Text('Toutes les Wilayas (58)', style: TextStyle(fontSize: 13)),
                      ),
                      ...state.availableWilayas.map((w) {
                        return DropdownMenuItem<String?>(
                          value: w.code,
                          child: Text('${w.code} - ${w.name}', style: const TextStyle(fontSize: 13)),
                        );
                      }),
                    ],
                    onChanged: (val) => notifier.setWilaya(val),
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // 2. Sélecteur des Communes (dépendant de la Wilaya)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: selectedWilaya == null ? Colors.grey.shade50 : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: selectedCommune != null ? Colors.teal.shade700 : Colors.grey.shade300,
                    width: selectedCommune != null ? 1.5 : 1.0,
                  ),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String?>(
                    key: const Key('commune_dropdown'),
                    value: selectedCommune,
                    hint: Text(
                      selectedWilaya == null ? 'Commune (Wilaya requise)' : 'Toutes les Communes',
                      style: TextStyle(
                        fontSize: 13,
                        color: selectedWilaya == null ? Colors.grey.shade400 : Colors.black87,
                      ),
                    ),
                    icon: const Icon(Icons.arrow_drop_down, size: 20),
                    isDense: true,
                    items: selectedWilaya == null
                        ? null
                        : [
                            const DropdownMenuItem<String?>(
                              value: null,
                              child: Text('Toutes les Communes', style: TextStyle(fontSize: 13)),
                            ),
                            ...state.availableCommunes.map((c) {
                              return DropdownMenuItem<String?>(
                                value: c.name,
                                child: Text(c.name, style: const TextStyle(fontSize: 13)),
                              );
                            }),
                          ],
                    onChanged: selectedWilaya == null ? null : (val) => notifier.setCommune(val),
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // 3. Sélecteur de Spécialités
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: selectedSpecialty != null ? Colors.teal.shade700 : Colors.grey.shade300,
                    width: selectedSpecialty != null ? 1.5 : 1.0,
                  ),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String?>(
                    key: const Key('specialty_dropdown'),
                    value: selectedSpecialty,
                    hint: const Text('Toutes spécialités', style: TextStyle(fontSize: 13)),
                    icon: const Icon(Icons.arrow_drop_down, size: 20),
                    isDense: true,
                    items: [
                      const DropdownMenuItem<String?>(
                        value: null,
                        child: Text('Toutes spécialités', style: TextStyle(fontSize: 13)),
                      ),
                      ...state.availableSpecialties.take(30).map((s) {
                        return DropdownMenuItem<String?>(
                          value: s,
                          child: Text(s, style: const TextStyle(fontSize: 13)),
                        );
                      }),
                    ],
                    onChanged: (val) => notifier.setSpecialty(val),
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // 4. Switch rapide "Pharmacie de garde"
              FilterChip(
                key: const Key('duty_filter_chip'),
                selected: isDutyActive,
                avatar: Icon(
                  Icons.nightlight_round,
                  size: 16,
                  color: isDutyActive ? Colors.white : Colors.amber.shade900,
                ),
                label: const Text('Garde 24/24', style: TextStyle(fontSize: 13)),
                selectedColor: Colors.teal.shade800,
                labelStyle: TextStyle(
                  color: isDutyActive ? Colors.white : Colors.black87,
                  fontWeight: isDutyActive ? FontWeight.bold : FontWeight.normal,
                ),
                checkmarkColor: Colors.white,
                onSelected: (val) => notifier.setOnlyOnDutyPharmacies(val),
              ),
            ],
          ),
        );
      },
    );
  }
}
