import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/models/health_facility.dart';
import '../../core/services/offline_health_search_service.dart';
import 'widgets/facility_detail_sheet.dart';
import 'widgets/facet_filter_bar.dart';

/// Visualiseur cartographique hors-ligne avec clustering et navigation par Wilaya (Santé DZ / Medizy)
class OfflineMapView extends StatefulWidget {
  final OfflineHealthSearchService searchService;
  final LatLng initialCenter;
  final double initialZoom;

  const OfflineMapView({
    Key? key,
    required this.searchService,
    this.initialCenter = const LatLng(28.0339, 1.6596), // Centre géographique de l'Algérie
    this.initialZoom = 5.8,
  }) : super(key: key);

  @override
  State<OfflineMapView> createState() => _OfflineMapViewState();
}

class _OfflineMapViewState extends State<OfflineMapView> {
  late final MapController _mapController;
  List<HealthFacility> _displayedFacilities = [];
  bool _isLoading = false;

  String? _selectedWilayaCode;
  String? _selectedCategory;
  bool _onlyEmergency = false;
  String _currentQuery = '';
  bool _useCartoDb = false;

  // Coordonnées GPS utilisateur par défaut (Alger - Place des Martyrs)
  LatLng _userPosition = const LatLng(36.7753, 3.0588);

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _loadInitialData();
  }

  void _loadInitialData() {
    setState(() => _isLoading = true);
    try {
      // Chargement initial des établissements principaux ou autour d'Alger
      final results = widget.searchService.searchAroundMe(
        latitude: _userPosition.latitude,
        longitude: _userPosition.longitude,
        radiusKm: 25.0,
        limit: 100,
      );
      setState(() {
        _displayedFacilities = results;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _applyFilters() {
    setState(() => _isLoading = true);
    try {
      final results = widget.searchService.searchHybrid(
        query: _currentQuery.isNotEmpty ? _currentQuery : null,
        wilayaCode: _selectedWilayaCode,
        category: _selectedCategory,
        onlyEmergency: _onlyEmergency,
        userLat: _userPosition.latitude,
        userLon: _userPosition.longitude,
        limit: 150,
      );

      setState(() {
        _displayedFacilities = results;
        _isLoading = false;
      });

      // Recadrage cartographique sur le premier résultat si disponible
      if (results.isNotEmpty) {
        final first = results.first;
        _mapController.move(
          LatLng(first.latitude, first.longitude),
          _selectedWilayaCode != null ? 10.5 : 12.0,
        );
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _zoomToNational() {
    _mapController.move(const LatLng(28.0339, 1.6596), 5.8);
  }

  void _zoomToUserPosition() {
    _mapController.move(_userPosition, 13.0);
    _applyFilters();
  }

  Color _getMarkerColor(HealthFacility facility) {
    if (facility.isEmergencyOrOnDuty) return Colors.red.shade700;
    final cat = facility.categorie.toLowerCase();
    if (cat.contains('pharmacie')) return Colors.green.shade700;
    if (cat.contains('hopital') || cat.contains('clinique')) return Colors.indigo.shade700;
    if (cat.contains('dentiste')) return Colors.teal.shade700;
    if (cat.contains('laboratoire')) return Colors.purple.shade700;
    return Colors.blue.shade700;
  }

  IconData _getMarkerIcon(HealthFacility facility) {
    if (facility.isEmergencyOrOnDuty) return Icons.emergency;
    final cat = facility.categorie.toLowerCase();
    if (cat.contains('pharmacie')) return Icons.local_pharmacy;
    if (cat.contains('hopital')) return Icons.local_hospital;
    if (cat.contains('dentiste')) return Icons.medical_services_outlined;
    if (cat.contains('laboratoire')) return Icons.biotech;
    return Icons.person;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Medizy', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            Text('Carte Sanitaire Hors-Ligne (58 Wilayas)', style: TextStyle(fontSize: 12)),
          ],
        ),
        backgroundColor: Colors.teal.shade800,
        foregroundColor: Colors.white,
        actions: [
          // Bascule dynamique entre OpenStreetMap et CartoDB Voyager
          IconButton(
            icon: Icon(_useCartoDb ? Icons.map : Icons.layers_outlined),
            tooltip: _useCartoDb
                ? 'Fond CartoDB Voyager actif (Cliquer pour OSM)'
                : 'Fond OSM Standard actif (Cliquer pour CartoDB)',
            onPressed: () => setState(() => _useCartoDb = !_useCartoDb),
          ),
          Center(
            child: Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.teal.shade900,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${_displayedFacilities.length} fiches',
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
                ),
              ),
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          // 1. Vue Cartographique flutter_map avec fond neutre médical hors-ligne
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: widget.initialCenter,
              initialZoom: widget.initialZoom,
              minZoom: 4.5,
              maxZoom: 18.0,
              backgroundColor: const Color(0xFFEFF3F4), // Fond neutre clair médical hors-ligne
            ),
            children: [
              // Tuiles cartographiques avec User-Agent réglementaire OSM et fallback CartoDB
              TileLayer(
                urlTemplate: _useCartoDb
                    ? 'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png'
                    : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                fallbackUrl: _useCartoDb
                    ? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
                    : 'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                userAgentPackageName: 'dz.sante.medizy.national',
                additionalOptions: const {
                  'User-Agent': 'Medizy-Algeria/1.0.17 (https://medizy.dz; contact@medizy.dz)',
                },
                tileProvider: NetworkTileProvider(
                  headers: {
                    'User-Agent': 'Medizy-Algeria/1.0.17 (dz.sante.medizy.national)',
                  },
                ),
                errorTileCallback: (tile, error, stackTrace) {
                  // Gestion gracieuse des erreurs de chargement réseau ou mode déconnecté
                },
                tileBuilder: (context, tileWidget, tile) {
                  return Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey.shade200, width: 0.1),
                    ),
                    child: tileWidget,
                  );
                },
              ),

              // Marqueur de position de l'utilisateur
              MarkerLayer(
                markers: [
                  Marker(
                    point: _userPosition,
                    width: 44,
                    height: 44,
                    child: const Icon(
                      Icons.my_location,
                      color: Colors.blueAccent,
                      size: 28,
                    ),
                  ),
                ],
              ),

              // Repères des établissements avec code couleur par catégorie et icônes
              MarkerLayer(
                markers: _displayedFacilities.map((fac) {
                  final color = _getMarkerColor(fac);
                  final icon = _getMarkerIcon(fac);

                  return Marker(
                    point: LatLng(fac.latitude, fac.longitude),
                    width: 38,
                    height: 38,
                    child: GestureDetector(
                      onTap: () => FacilityDetailSheet.show(context, fac),
                      child: Container(
                        decoration: BoxDecoration(
                          color: color,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                          boxShadow: const [
                            BoxShadow(
                              color: Colors.black26,
                              blurRadius: 4,
                              offset: Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Icon(
                          icon,
                          color: Colors.white,
                          size: 20,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),

          // 2. Barre de filtrage supérieure à facettes
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: FacetFilterBar(
              selectedWilayaCode: _selectedWilayaCode,
              selectedCategory: _selectedCategory,
              onlyEmergency: _onlyEmergency,
              onWilayaChanged: (w) {
                setState(() => _selectedWilayaCode = w);
                _applyFilters();
              },
              onCategoryChanged: (cat) {
                setState(() => _selectedCategory = cat);
                _applyFilters();
              },
              onEmergencyToggled: (em) {
                setState(() => _onlyEmergency = em);
                _applyFilters();
              },
              onSearchSubmitted: (q) {
                setState(() => _currentQuery = q);
                _applyFilters();
              },
            ),
          ),

          // 3. Indicateur de chargement
          if (_isLoading)
            const Positioned(
              top: 110,
              left: 0,
              right: 0,
              child: Center(
                child: Card(
                  elevation: 4,
                  child: Padding(
                    padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        SizedBox(width: 12),
                        Text('Recherche locale SQLite en cours...'),
                      ],
                    ),
                  ),
                ),
              ),
            ),

          // 4. Boutons d'action flottants (National / Autour de moi)
          Positioned(
            bottom: 24,
            right: 16,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                FloatingActionButton.small(
                  heroTag: 'fab_national',
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.teal.shade800,
                  tooltip: 'Vue Nationale (58 Wilayas)',
                  onPressed: _zoomToNational,
                  child: const Icon(Icons.public),
                ),
                const SizedBox(height: 10),
                FloatingActionButton(
                  heroTag: 'fab_my_location',
                  backgroundColor: Colors.teal.shade700,
                  foregroundColor: Colors.white,
                  tooltip: 'Autour de moi (5 km)',
                  onPressed: _zoomToUserPosition,
                  child: const Icon(Icons.near_me),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
