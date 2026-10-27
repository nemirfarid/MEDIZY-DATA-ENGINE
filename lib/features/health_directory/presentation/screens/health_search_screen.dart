import 'package:flutter/material.dart';
import '../../state/health_favorites_notifier.dart';
import '../../state/health_search_notifier.dart';
import '../../state/health_sync_engine.dart';
import '../widgets/health_detail_sheet.dart';
import '../widgets/health_directory_map_view.dart';
import '../widgets/health_filter_bar.dart';
import '../widgets/health_professional_card.dart';
import '../widgets/sync_status_badge.dart';

/// Écran principal de recherche et consultation de l'annuaire de santé
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
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text(
          'Santé DZ / Annuaire National',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17),
        ),
        backgroundColor: Colors.teal.shade800,
        foregroundColor: Colors.white,
        elevation: 0,
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
          // 1. Champ de recherche textuelle avec icône d'effacement
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 4),
            child: TextField(
              key: const Key('search_text_field'),
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Rechercher médecin, pharmacie, clinique...',
                hintStyle: TextStyle(color: Colors.grey.shade500, fontSize: 14),
                prefixIcon: const Icon(Icons.search, color: Colors.teal),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          widget.notifier.onSearchQueryChanged('');
                          setState(() {});
                        },
                      )
                    : null,
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                filled: true,
                fillColor: const Color(0xFFF5F7F8),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Colors.grey.shade200),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Colors.grey.shade200),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: Colors.teal.shade700, width: 1.5),
                ),
              ),
              onChanged: (text) {
                widget.notifier.onSearchQueryChanged(text);
                setState(() {});
              },
            ),
          ),

          // 2. Barre de filtres (Wilayas 01-58, Communes, Spécialités, Garde, Favoris)
          HealthFilterBar(
            notifier: widget.notifier,
            isFavoritesOnly: _isFavoritesOnly,
            onFavoritesOnlyChanged: widget.favoritesNotifier != null
                ? (val) => setState(() => _isFavoritesOnly = val)
                : null,
          ),
          const Divider(height: 1),

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

                // Affichage Vue Liste selon le statut
                if (!_isFavoritesOnly && state.isLoading) {
                  return const Center(
                    key: Key('loading_indicator'),
                    child: CircularProgressIndicator(),
                  );
                }

                if (!_isFavoritesOnly && state.isError) {
                  return Center(
                    key: const Key('error_view'),
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.error_outline, size: 48, color: Colors.red.shade400),
                          const SizedBox(height: 12),
                          Text(
                            state.failure?.message ?? 'Une erreur est survenue.',
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 14, color: Colors.black87),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: () => widget.notifier.search(isLoadMore: false),
                            child: const Text('Réessayer'),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                if (displayedList.isEmpty) {
                  return Center(
                    key: const Key('empty_view'),
                    child: Padding(
                      padding: const EdgeInsets.all(32),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            _isFavoritesOnly ? Icons.star_border : Icons.search_off,
                            size: 56,
                            color: Colors.grey.shade400,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _isFavoritesOnly
                                ? 'Aucun favori enregistré.'
                                : 'Aucun établissement trouvé pour ces critères.',
                            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _isFavoritesOnly
                                ? 'Touchez l\'étoile sur une fiche pour l\'ajouter à vos favoris hors-ligne.'
                                : 'Essayez d\'ajuster vos filtres de Wilaya, Commune ou Spécialité.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                          ),
                        ],
                      ),
                    ),
                  );
                }

                // Liste des résultats (ou favoris)
                return RefreshIndicator(
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
                    padding: const EdgeInsets.only(top: 8, bottom: 24),
                    itemCount: displayedList.length + (!_isFavoritesOnly && state.isLoadingMore ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index == displayedList.length) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 16),
                          child: Center(
                            child: SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(strokeWidth: 2),
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
