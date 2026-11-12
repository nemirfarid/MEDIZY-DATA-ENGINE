import 'package:flutter/material.dart';
import '../../../../core/theme/medizy_theme.dart';
import '../../state/health_favorites_notifier.dart';
import '../../state/health_search_notifier.dart';
import '../../state/health_sync_engine.dart';
import '../widgets/health_detail_sheet.dart';
import '../widgets/health_directory_map_view.dart';
import '../widgets/health_filter_bar.dart';
import '../widgets/health_professional_card.dart';
import '../widgets/sync_status_badge.dart';

/// Écran principal de recherche et consultation de l'annuaire de santé (Design Premium)
class HealthSearchScreen extends StatefulWidget {
  final HealthSearchNotifier notifier;
  final HealthFavoritesNotifier? favoritesNotifier;
  final HealthSyncEngine? syncEngine;
  final bool enableMapTiles;

  const HealthSearchScreen({
    super.key,
    required this.notifier,
    this.favoritesNotifier,
    this.syncEngine,
    this.enableMapTiles = true,
  });

  @override
  State<HealthSearchScreen> createState() => _HealthSearchScreenState();
}

class _HealthSearchScreenState extends State<HealthSearchScreen> {
  late final TextEditingController _searchController;
  late final ScrollController _scrollController;
  bool _isMapView = false;
  bool _isFavoritesOnly = false;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(
      text: widget.notifier.state.filter.query ?? '',
    );
    _scrollController = ScrollController()..addListener(_onScroll);

    // Initialisation des Wilayas si pas encore chargées
    if (widget.notifier.state.availableWilayas.isEmpty) {
      widget.notifier.initialize();
    }
  }

  void _onScroll() {
    if (!_scrollController.hasClients || _isFavoritesOnly) return;
    final maxScroll = _scrollController.position.maxScrollExtent;
    final currentScroll = _scrollController.position.pixels;

    // Déclenchement de la pagination à 80% du défilement
    if (currentScroll >= maxScroll - 250) {
      widget.notifier.loadMore();
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final listenable = widget.favoritesNotifier != null
        ? Listenable.merge([widget.notifier, widget.favoritesNotifier!])
        : widget.notifier;

    return Scaffold(
      backgroundColor: MedizyTheme.background,
      appBar: AppBar(
        title: const Text(
          'Santé DZ / Annuaire National',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
        ),
        backgroundColor: MedizyTheme.primaryDark,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        actions: [
          if (widget.syncEngine != null)
            SyncStatusBadge(syncEngine: widget.syncEngine!),
          IconButton(
            key: const Key('toggle_view_mode_button'),
            icon: Icon(_isMapView ? Icons.format_list_bulleted : Icons.map_outlined),
            tooltip: _isMapView ? 'Afficher la liste' : 'Afficher la carte',
            onPressed: () {
              setState(() {
                _isMapView = !_isMapView;
              });
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // 1. Champ de recherche textuelle avec design Premium
          Container(
            color: MedizyTheme.surface,
            padding: EdgeInsets.fromLTRB(MedizyTheme.spacingM, MedizyTheme.spacingS, MedizyTheme.spacingM, MedizyTheme.spacingM),
            child: TextField(
              key: const Key('search_text_field'),
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Rechercher médecin, pharmacie, clinique...',
                hintStyle: TextStyle(color: MedizyTheme.textSecondary, fontSize: 14),
                prefixIcon: const Icon(Icons.search, color: MedizyTheme.primary),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.backspace_outlined, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          widget.notifier.onSearchQueryChanged('');
                          setState(() {});
                        },
                      )
                    : null,
                contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                filled: true,
                fillColor: MedizyTheme.background,
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
              onChanged: (text) {
                widget.notifier.onSearchQueryChanged(text);
                setState(() {});
              },
            ),
          ),

          // 2. Barre de filtres
          HealthFilterBar(
            notifier: widget.notifier,
            isFavoritesOnly: _isFavoritesOnly,
            onFavoritesOnlyChanged: widget.favoritesNotifier != null
                ? (val) => setState(() => _isFavoritesOnly = val)
                : null,
          ),
          const Divider(height: 1, color: Colors.black12),

          // 3. Zone principale dynamique : Carte ou Liste selon bascule
          Expanded(
            child: ListenableBuilder(
              listenable: listenable,
              builder: (context, _) {
                final state = widget.notifier.state;
                final displayedList = _isFavoritesOnly
                    ? (widget.favoritesNotifier?.favorites ?? [])
                    : state.results;

                // Affichage Vue Cartographique
                if (_isMapView) {
                  return HealthDirectoryMapView(
                    facilities: displayedList,
                    enableTiles: widget.enableMapTiles,
                    activeCategory: state.selectedCategory,
                    onClearCategory: () => widget.notifier.setCategory(null),
                    onFacilitySelected: (facility) {
                      _showDetail(context, facility);
                    },
                  );
                }

                // Affichage Chargement Premium
                if (!_isFavoritesOnly && state.isLoading) {
                  return Center(
                    key: const Key('loading_indicator'),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const CircularProgressIndicator(color: MedizyTheme.primary),
                        const SizedBox(height: MedizyTheme.spacingM),
                        Text(
                          'Chargement de l\'annuaire...',
                          style: TextStyle(color: MedizyTheme.textSecondary, fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                  );
                }

                // Affichage Erreur
                if (!_isFavoritesOnly && state.isError) {
                  return Center(
                    key: const Key('error_view'),
                    child: Padding(
                      padding: EdgeInsets.all(MedizyTheme.spacingL),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.error_outline, size: 48, color: MedizyTheme.error),
                          const SizedBox(height: MedizyTheme.spacingS),
                          Text(
                            state.failure?.message ?? 'Une erreur est survenue.',
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 14, color: MedizyTheme.textPrimary),
                          ),
                          const SizedBox(height: MedizyTheme.spacingM),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: MedizyTheme.primary,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                              ),
                            ),
                            onPressed: () => widget.notifier.search(isLoadMore: false),
                            child: const Text('Réessayer'),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                // Affichage Liste Vide
                if (displayedList.isEmpty) {
                  return Center(
                    key: const Key('empty_view'),
                    child: Padding(
                      padding: EdgeInsets.all(MedizyTheme.spacingL),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            _isFavoritesOnly ? Icons.star_border : Icons.search_off,
                            size: 56,
                            color: MedizyTheme.textSecondary,
                          ),
                          const SizedBox(height: MedizyTheme.spacingM),
                          Text(
                            _isFavoritesOnly
                                ? 'Aucun favori enregistré.'
                                : 'Aucun établissement trouvé pour ces critères.',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: MedizyTheme.textPrimary),
                          ),
                          const SizedBox(height: MedizyTheme.spacingS),
                          Text(
                            _isFavoritesOnly
                                ? 'Touchez l\'étoile sur une fiche pour l\'ajouter à vos favoris hors-ligne.'
                                : 'Essayez d\'ajuster vos filtres de Wilaya, Commune ou Spécialité.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 13, color: MedizyTheme.textSecondary),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                // Liste des résultats (ou favoris)
                return RefreshIndicator(
                  color: MedizyTheme.primary,
                  onRefresh: () async {
                    if (_isFavoritesOnly) {
                      await widget.favoritesNotifier?.initialize();
                    } else {
                      await widget.notifier.search(isLoadMore: false);
                    }
                  },
                  child: ListView.builder(
                    key: const Key('results_list_view'),
                    controller: _scrollController,
                    padding: EdgeInsets.only(top: MedizyTheme.spacingS, bottom: MedizyTheme.spacingL),
                    itemCount: displayedList.length + (!_isFavoritesOnly && state.isLoadingMore ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == displayedList.length) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: MedizyTheme.spacingM),
                          child: Center(
                            child: SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(strokeWidth: 2, color: MedizyTheme.primary),
                            ),
                          ),
                        );
                      }

                      final item = displayedList[index];
                      final isFav = widget.favoritesNotifier?.isFavorite(item.id) ?? false;

                      return HealthProfessionalCard(
                        professional: item,
                        isFavorite: isFav,
                        onFavoriteToggle: widget.favoritesNotifier != null
                            ? () => widget.favoritesNotifier!.toggleFavorite(item)
                            : null,
                        onTap: () => _showDetail(context, item),
                        onCallPressed: () => _showDetail(context, item),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showDetail(BuildContext context, dynamic item) {
    widget.favoritesNotifier?.recordView(item);

    HealthDetailSheet.show(
      context,
      item,
      isFavorite: widget.favoritesNotifier?.isFavorite(item.id) ?? false,
      onFavoriteToggle: widget.favoritesNotifier != null
          ? () => widget.favoritesNotifier!.toggleFavorite(item)
          : null,
      onReportSubmitted: widget.favoritesNotifier != null
          ? (report) => widget.favoritesNotifier!.submitReport(report)
          : null,
    );
  }
}
