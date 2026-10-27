import 'package:flutter/material.dart';
import '../../../../core/models/health_search_filter.dart';
import '../../../../core/services/offline_health_search_service.dart';
import '../../../emergency/presentation/widgets/sos_emergency_button.dart';
import '../../../health_directory/presentation/screens/health_search_screen.dart';
import '../../../health_directory/services/health_directory_service.dart';
import '../../../health_directory/state/health_search_notifier.dart';
import '../../../map/offline_map_view.dart';
import '../widgets/category_grid.dart';

/// Page d'accueil épurée et moderne MEDIZY
/// Présente une vue claire et aérée avec uniquement une grille responsive
/// de catégories de santé, accès direct à la cartographie et transmission réactive d'état.
class MedizyHomeScreen extends StatefulWidget {
  final OfflineHealthSearchService searchService;
  final HealthSearchNotifier? notifier;

  const MedizyHomeScreen({
    super.key,
    required this.searchService,
    this.notifier,
  });

  @override
  State<MedizyHomeScreen> createState() => _MedizyHomeScreenState();
}

class _MedizyHomeScreenState extends State<MedizyHomeScreen> {
  late final HealthSearchNotifier _notifier;

  @override
  void initState() {
    super.initState();
    _notifier = widget.notifier ??
        HealthSearchNotifier(
          directoryService: HealthDirectoryService(),
        );
  }

  void _onCategorySelected(String slug) {
    // 1. Transmission réactive d'état vers HealthSearchNotifier
    _notifier.setFilter(HealthSearchFilter(category: slug));

    // 2. Navigation vers la carte avec filtre immédiatement actif
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => OfflineMapView(
          searchService: widget.searchService,
          initialCategory: slug,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7FAFA),
      appBar: AppBar(
        elevation: 0,
        backgroundColor: Colors.teal.shade800,
        foregroundColor: Colors.white,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.health_and_safety_rounded,
                size: 20,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 10),
            const Text(
              'MEDIZY',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 18,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search_rounded),
            tooltip: 'Recherche et Annuaire',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => HealthSearchScreen(notifier: _notifier),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.map_rounded),
            tooltip: 'Ouvrir la carte',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => OfflineMapView(searchService: widget.searchService),
                ),
              );
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Bandeau d'en-tête sobre
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border(
                  bottom: BorderSide(
                    color: Colors.grey.shade200,
                    width: 1,
                  ),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Annuaire Sanitaire National',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.teal.shade900,
                      letterSpacing: -0.2,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Sélectionnez une catégorie pour consulter la carte hors-ligne (58 Wilayas)',
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
            ),

            // Grille épurée de catégories (responsive 3 ou 4 colonnes)
            Expanded(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: CategoryGrid(
                  searchService: widget.searchService,
                  onCategorySelected: _onCategorySelected,
                ),
              ),
            ),

            // Barre d'action inférieure : Explorer la Carte Nationale
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 10,
                    offset: const Offset(0, -3),
                  ),
                ],
              ),
              child: SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => OfflineMapView(searchService: widget.searchService),
                      ),
                    );
                  },
                  icon: const Icon(Icons.travel_explore_rounded, size: 20),
                  label: const Text(
                    'Explorer la Carte Nationale',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.teal.shade800,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    elevation: 1,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: SosEmergencyButton(
        searchService: widget.searchService,
      ),
    );
  }
}
