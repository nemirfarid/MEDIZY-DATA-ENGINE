import 'package:flutter/material.dart';
import '../../models/dz_medication.dart';
import '../../services/dz_medication_service.dart';

/// Modal / BottomSheet de recherche et d'affichage instantané des Équivalents & Génériques DCI en Algérie.
/// Permet de pallier immédiatement aux ruptures de stock en trouvant les substituts locaux (ex: Saidal, Biopharm).
class DciEquivalentsSheet extends StatefulWidget {
  final DzMedicationService medicationService;
  final String? initialQuery;
  final void Function(DzMedication medication)? onSelectEquivalent;

  const DciEquivalentsSheet({
    super.key,
    required this.medicationService,
    this.initialQuery,
    this.onSelectEquivalent,
  });

  static Future<void> show(
    BuildContext context, {
    required DzMedicationService medicationService,
    String? initialQuery,
    void Function(DzMedication medication)? onSelectEquivalent,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => DciEquivalentsSheet(
        medicationService: medicationService,
        initialQuery: initialQuery,
        onSelectEquivalent: onSelectEquivalent,
      ),
    );
  }

  @override
  State<DciEquivalentsSheet> createState() => _DciEquivalentsSheetState();
}

class _DciEquivalentsSheetState extends State<DciEquivalentsSheet> {
  late final TextEditingController _searchController;
  DciEquivalenceResult? _result;
  bool _isLoading = false;

  final List<String> _quickSuggestions = [
    'Doliprane',
    'Augmentin',
    'Glucophage',
    'Tahor',
    'Mopral',
    'Ventoline',
    'Kardegic',
    'Spasfon',
  ];

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(text: widget.initialQuery ?? 'Doliprane');
    _performSearch(_searchController.text);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _performSearch(String query) {
    if (query.trim().isEmpty) {
      setState(() {
        _result = null;
        _isLoading = false;
      });
      return;
    }

    setState(() => _isLoading = true);
    final res = widget.medicationService.getEquivalentsFor(query.trim());
    setState(() {
      _result = res;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Color(0xFFF8FAFC),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // Barre de poignée supérieure
              Center(
                child: Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 8),
                  width: 48,
                  height: 5,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2.5),
                  ),
                ),
              ),

              // En-tête avec titre et badge DCI
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.teal.shade50,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(Icons.medication_rounded, color: Colors.teal.shade800, size: 24),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Équivalents & Génériques (DCI)',
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.teal.shade900,
                            ),
                          ),
                          Text(
                            'Alternative immédiate en cas de rupture de stock',
                            style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),

              // Champ de recherche FTS5
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: TextField(
                  key: const Key('dci_search_field'),
                  controller: _searchController,
                  onChanged: _performSearch,
                  decoration: InputDecoration(
                    hintText: 'Nom du médicament (ex: Doliprane, Augmentin...)',
                    hintStyle: TextStyle(fontSize: 13.5, color: Colors.grey.shade500),
                    prefixIcon: const Icon(Icons.search_rounded, color: Colors.teal),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              _performSearch('');
                            },
                          )
                        : null,
                    filled: true,
                    fillColor: Colors.white,
                    contentPadding: const EdgeInsets.symmetric(vertical: 12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide(color: Colors.grey.shade300),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide(color: Colors.grey.shade200),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide(color: Colors.teal.shade700, width: 1.5),
                    ),
                  ),
                ),
              ),

              // Suggestions rapides de médicaments fréquents
              SizedBox(
                height: 38,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: _quickSuggestions.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final name = _quickSuggestions[index];
                    final isSelected = _searchController.text.toLowerCase() == name.toLowerCase();
                    return ActionChip(
                      label: Text(name),
                      labelStyle: TextStyle(
                        fontSize: 12,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        color: isSelected ? Colors.white : Colors.teal.shade900,
                      ),
                      backgroundColor: isSelected ? Colors.teal.shade800 : Colors.teal.shade50,
                      side: BorderSide(color: isSelected ? Colors.teal.shade800 : Colors.teal.shade100),
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      onPressed: () {
                        _searchController.text = name;
                        _performSearch(name);
                      },
                    );
                  },
                ),
              ),
              const SizedBox(height: 8),

              // Contenu principal déroulant
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator(strokeWidth: 2))
                    : (_result == null || !_result!.hasEquivalents)
                        ? _buildEmptyState()
                        : ListView(
                            controller: scrollController,
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                            children: [
                              // 1. Synthèse DCI identifiée
                              _buildDciBanner(_result!),
                              const SizedBox(height: 14),

                              // 2. Génériques Algériens Recommandés (Production Nationale)
                              if (_result!.localProducers.isNotEmpty) ...[
                                _buildSectionHeader(
                                  title: 'Production Nationale Algérienne 🇩🇿',
                                  subtitle: 'Génériques disponibles localement (Saidal, Biopharm...)',
                                  color: Colors.teal.shade900,
                                ),
                                const SizedBox(height: 8),
                                ..._result!.localProducers.map((m) => _buildMedicationCard(m, isHighlighted: true)),
                                const SizedBox(height: 16),
                              ],

                              // 3. Autres Équivalents & Princeps de référence
                              if (_result!.allEquivalents.any((m) => !m.isLocalProducer)) ...[
                                _buildSectionHeader(
                                  title: 'Autres Formes & Marques Internationales',
                                  subtitle: 'Partageant la même DCI (${_result!.dci})',
                                  color: Colors.blueGrey.shade800,
                                ),
                                const SizedBox(height: 8),
                                ..._result!.allEquivalents
                                    .where((m) => !m.isLocalProducer)
                                    .map((m) => _buildMedicationCard(m, isHighlighted: false)),
                              ],
                            ],
                          ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildDciBanner(DciEquivalenceResult res) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.teal.shade200),
        boxShadow: [
          BoxShadow(
            color: Colors.teal.withValues(alpha: 0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.teal.shade700,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'DCI ACTIVE',
                  style: TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  res.dci,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.teal.shade900,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${res.count} équivalent(s) thérapeutique(s) identifié(s) dans la pharmacopée nationale.',
            style: TextStyle(fontSize: 12.5, color: Colors.grey.shade700),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader({
    required String title,
    required String subtitle,
    required Color color,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          subtitle,
          style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
        ),
      ],
    );
  }

  Widget _buildMedicationCard(DzMedication med, {required bool isHighlighted}) {
    return Card(
      key: Key('med_card_${med.id}'),
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: isHighlighted ? Colors.teal.shade300 : Colors.grey.shade200,
          width: isHighlighted ? 1.5 : 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Icône forme galénique
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isHighlighted ? Colors.teal.shade50 : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                _getFormIcon(med.forme),
                size: 22,
                color: isHighlighted ? Colors.teal.shade800 : Colors.blueGrey.shade700,
              ),
            ),
            const SizedBox(width: 12),

            // Détails du médicament
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          med.nomCommercial,
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Colors.blueGrey.shade900,
                          ),
                        ),
                      ),
                      if (med.remboursableChifa)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.green.shade50,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(color: Colors.green.shade600, width: 0.8),
                          ),
                          child: Text(
                            'CHIFA',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: Colors.green.shade800,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '${med.dosage} • ${med.forme}',
                    style: TextStyle(fontSize: 12.5, color: Colors.grey.shade700),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(Icons.business_rounded, size: 13, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Text(
                        'Labo : ${med.laboratoire}',
                        style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
                      ),
                      if (med.prixDzd != null) ...[
                        const Spacer(),
                        Text(
                          '${med.prixDzd!.toStringAsFixed(0)} DZD',
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.bold,
                            color: Colors.teal.shade900,
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getFormIcon(String forme) {
    final f = forme.toLowerCase();
    if (f.contains('sirop') || f.contains('suspension')) {
      return Icons.liquor_rounded;
    } else if (f.contains('aérosol') || f.contains('spray')) {
      return Icons.air_rounded;
    } else if (f.contains('injectable')) {
      return Icons.vaccines_rounded;
    } else if (f.contains('sachet')) {
      return Icons.inventory_2_rounded;
    }
    return Icons.medication_rounded;
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.search_off_rounded, size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(
              'Aucun équivalent trouvé',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.grey.shade700),
            ),
            const SizedBox(height: 4),
            Text(
              'Essayez un autre nom de médicament ou DCI (ex: Doliprane, Augmentin, Tahor...).',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12.5, color: Colors.grey.shade500),
            ),
          ],
        ),
      ),
    );
  }
}
