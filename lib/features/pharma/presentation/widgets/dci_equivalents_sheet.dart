import 'package:flutter/material.dart';
import '../../../../core/theme/medizy_theme.dart';
import '../../models/dz_medication.dart';
import '../../services/dz_medication_service.dart';

/// Modal / BottomSheet de recherche et d'affichage instantané des Équivalents & Génériques DCI en Algérie (Design Premium).
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
      initialChildSize: 0.88,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: MedizyTheme.surface,
            borderRadius: BorderRadius.vertical(top: Radius.circular(MedizyTheme.borderRadiusL)),
            boxShadow: const [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 16,
                offset: Offset(0, -4),
              ),
            ],
          ),
          child: Column(
            children: [
              // Barre de poignée supérieure ergonomique
              const SizedBox(height: 12),
              Container(
                width: 48,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2.5),
                ),
              ),
              const SizedBox(height: 8),

              // En-tête avec titre et badge DCI
              Padding(
                padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM, vertical: 8),
                child: Row(
                  children: [
                    Container(
                      padding: EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: MedizyTheme.primary.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.medication_rounded, color: MedizyTheme.primary, size: 26),
                    ),
                    const SizedBox(width: MedizyTheme.spacingS),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Équivalents & Génériques (DCI)',
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: MedizyTheme.primaryDark,
                            ),
                          ),
                          Text(
                            'Alternative immédiate en cas de rupture de stock',
                            style: theme.textTheme.bodySmall?.copyWith(color: MedizyTheme.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close_rounded, size: 24),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),

              // Champ de recherche FTS5 Premium
              Padding(
                padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM, vertical: 6),
                child: TextField(
                  key: const Key('dci_search_field'),
                  controller: _searchController,
                  onChanged: _performSearch,
                  decoration: InputDecoration(
                    hintText: 'Nom du médicament (ex: Doliprane, Augmentin...)',
                    hintStyle: TextStyle(fontSize: 14, color: MedizyTheme.textSecondary),
                    prefixIcon: const Icon(Icons.search_rounded, color: MedizyTheme.primary),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.backspace_outlined, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              _performSearch('');
                            },
                          )
                        : null,
                    filled: true,
                    fillColor: MedizyTheme.background,
                    contentPadding: EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                      borderSide: BorderSide.none,
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                      borderSide: BorderSide.none,
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                      borderSide: const BorderSide(color: MedizyTheme.primary, width: 1.5),
                    ),
                  ),
                ),
              ),

              // Suggestions rapides de médicaments fréquents
              SizedBox(
                height: 42,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM),
                  itemCount: _quickSuggestions.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final name = _quickSuggestions[index];
                    final isSelected = _searchController.text.toLowerCase() == name.toLowerCase();
                    return ActionChip(
                      label: Text(name),
                      labelStyle: TextStyle(
                        fontSize: 12.5,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        color: isSelected ? Colors.white : MedizyTheme.primaryDark,
                      ),
                      backgroundColor: isSelected ? MedizyTheme.primary : MedizyTheme.primary.withValues(alpha: 0.08),
                      side: BorderSide(color: isSelected ? MedizyTheme.primary : MedizyTheme.primary.withValues(alpha: 0.2)),
                      padding: EdgeInsets.symmetric(horizontal: 6),
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
                    ? const Center(child: CircularProgressIndicator(strokeWidth: 2, color: MedizyTheme.primary))
                    : (_result == null || !_result!.hasEquivalents)
                        ? _buildEmptyState()
                        : ListView(
                            controller: scrollController,
                            padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM, vertical: 8),
                            children: [
                              // 1. Synthèse DCI identifiée
                              _buildDciBanner(_result!),
                              const SizedBox(height: MedizyTheme.spacingM),

                              // 2. Génériques Algériens Recommandés (Production Nationale)
                              if (_result!.localProducers.isNotEmpty) ...[
                                _buildSectionHeader(
                                  title: 'Production Nationale Algérienne 🇩🇿',
                                  subtitle: 'Génériques disponibles localement (Saidal, Biopharm...)',
                                  color: MedizyTheme.primaryDark,
                                ),
                                const SizedBox(height: MedizyTheme.spacingS),
                                ..._result!.localProducers.map((m) => _buildMedicationCard(m, isHighlighted: true)),
                                const SizedBox(height: MedizyTheme.spacingM),
                              ],

                              // 3. Autres Équivalents & Princeps de référence
                              if (_result!.allEquivalents.any((m) => !m.isLocalProducer)) ...[
                                _buildSectionHeader(
                                  title: 'Autres Formes & Marques Internationales',
                                  subtitle: 'Partageant la même DCI (${_result!.dci})',
                                  color: MedizyTheme.textPrimary,
                                ),
                                const SizedBox(height: MedizyTheme.spacingS),
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
      padding: EdgeInsets.all(MedizyTheme.spacingM),
      decoration: BoxDecoration(
        color: MedizyTheme.surface,
        borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
        border: Border.all(color: MedizyTheme.primary.withValues(alpha: 0.3)),
        boxShadow: [
          BoxShadow(
            color: MedizyTheme.primary.withValues(alpha: 0.05),
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
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: MedizyTheme.primary,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'DCI ACTIVE',
                  style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  res.dci,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: MedizyTheme.primaryDark,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '${res.count} équivalent(s) thérapeutique(s) identifié(s) dans la pharmacopée nationale.',
            style: TextStyle(fontSize: 13, color: MedizyTheme.textSecondary),
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
            fontSize: 14.5,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          subtitle,
          style: TextStyle(fontSize: 12, color: MedizyTheme.textSecondary),
        ),
      ],
    );
  }

  Widget _buildMedicationCard(DzMedication med, {required bool isHighlighted}) {
    return Card(
      key: Key('med_card_${med.id}'),
      margin: EdgeInsets.only(bottom: 10),
      elevation: 1,
      color: MedizyTheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
        side: BorderSide(
          color: isHighlighted ? MedizyTheme.primary.withValues(alpha: 0.4) : Colors.grey.shade200,
          width: isHighlighted ? 1.5 : 1,
        ),
      ),
      child: Padding(
        padding: EdgeInsets.all(MedizyTheme.spacingM),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Icône forme galénique stylisée
            Container(
              padding: EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isHighlighted ? MedizyTheme.primary.withValues(alpha: 0.1) : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
              ),
              child: Icon(
                _getFormIcon(med.forme),
                size: 24,
                color: isHighlighted ? MedizyTheme.primary : MedizyTheme.textSecondary,
              ),
            ),
            const SizedBox(width: MedizyTheme.spacingS),

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
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: MedizyTheme.textPrimary,
                          ),
                        ),
                      ),
                      if (med.remboursableChifa)
                        Container(
                          padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: Colors.green.shade50,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: Colors.green.shade600, width: 0.8),
                          ),
                          child: Text(
                            'CHIFA',
                            style: TextStyle(
                              fontSize: 10.5,
                              fontWeight: FontWeight.bold,
                              color: Colors.green.shade800,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${med.dosage} • ${med.forme}',
                    style: TextStyle(fontSize: 13, color: MedizyTheme.textSecondary),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      const Icon(Icons.business_rounded, size: 14, color: MedizyTheme.textSecondary),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          'Labo : ${med.laboratoire}',
                          style: TextStyle(fontSize: 12, color: MedizyTheme.textSecondary),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (med.prixDzd != null) ...[
                        const SizedBox(width: 8),
                        Text(
                          '${med.prixDzd!.toStringAsFixed(0)} DZD',
                          style: const TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.bold,
                            color: MedizyTheme.primary,
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
        padding: EdgeInsets.all(MedizyTheme.spacingL),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.search_off_rounded, size: 56, color: MedizyTheme.textSecondary),
            const SizedBox(height: MedizyTheme.spacingM),
            const Text(
              'Aucun équivalent trouvé',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: MedizyTheme.textPrimary),
            ),
            const SizedBox(height: 6),
            Text(
              'Essayez un autre nom de médicament ou DCI (ex: Doliprane, Augmentin, Tahor...).',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: MedizyTheme.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
