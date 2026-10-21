import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/constants/algeria_wilayas.dart';
import '../../core/models/health_facility.dart';
import '../../core/services/location_service.dart';
import '../../core/services/offline_health_search_service.dart';
import 'widgets/facility_detail_sheet.dart';
import 'widgets/facet_filter_bar.dart';
import 'widgets/wilaya_picker_sheet.dart';

/// Visualiseur cartographique hors-ligne avec géolocalisation réelle, sélecteur des 58 Wilayas et moteur R-Tree/FTS5
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
  String? _selectedWilayaName;
  String? _selectedCategory;
  bool _onlyEmergency = false;
  String _currentQuery = '';
  bool _useCartoDb = false;

  // Position utilisateur réelle (par défaut Alger avant détection GPS)
  LatLng _userPosition = LocationService.defaultPosition;
  bool _hasRealGps = false;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _initAppAndLocation();
  }

  /// Initialisation au démarrage : tentative de géolocalisation passive puis chargement des données
  Future<void> _initAppAndLocation() async {
    setState(() => _isLoading = true);

    try {
      // 1. Tenter de récupérer la position GPS sans forcer le popup si permission non accordée
      final detectedPos = await LocationService.getCurrentLocation(promptPermission: false);
      if (detectedPos != null && mounted) {
        _userPosition = detectedPos;
        _hasRealGps = true;
      }

      // 2. Chargement initial : si géolocalisé, chercher autour ; sinon charger selon la wilaya active ou vue nationale
      final results = widget.searchService.searchHybrid(
        query: _currentQuery.isNotEmpty ? _currentQuery : null,
        wilayaCode: _selectedWilayaCode,
        category: _selectedCategory,
        onlyEmergency: _onlyEmergency,
        userLat: _userPosition.latitude,
        userLon: _userPosition.longitude,
        limit: 150,
      );

      if (mounted) {
        setState(() {
          _displayedFacilities = results;
          _isLoading = false;
        });

        // Recentrage sur la position détectée si GPS actif
        if (_hasRealGps) {
          _mapController.move(_userPosition, 13.5);
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  /// Actualisation des données selon les filtres actifs
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
        limit: 200,
      );

      setState(() {
        _displayedFacilities = results;
        _isLoading = false;
      });

      // Si des résultats existent et qu'une recherche textuelle vient d'être tapée, centrer sur le premier résultat
      if (_currentQuery.isNotEmpty && results.isNotEmpty) {
        final first = results.first;
        _mapController.move(LatLng(first.latitude, first.longitude), 13.0);
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  /// Sollicite activement le capteur GPS du smartphone et recentre la caméra
  Future<void> _handleGpsLocationRequest() async {
    setState(() => _isLoading = true);

    // 1. Vérification si le service GPS est activé sur l'appareil
    final isEnabled = await LocationService.isServiceEnabled();
    if (!isEnabled && mounted) {
      setState(() => _isLoading = false);
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.location_off, color: Colors.orange),
              SizedBox(width: 8),
              Text('GPS Désactivé'),
            ],
          ),
          content: const Text(
            'Veuillez activer le service de localisation (GPS) dans les paramètres de votre téléphone pour afficher les établissements les plus proches de vous.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      return;
    }

    // 2. Récupération de la position GPS précise
    final realPos = await LocationService.getCurrentLocation(promptPermission: true);
    if (!mounted) return;

    if (realPos != null) {
      setState(() {
        _userPosition = realPos;
        _hasRealGps = true;
      });

      // Recentrage caméra sur la vraie position
      _mapController.move(realPos, 14.0);

      // Recherche spatiale autour de la position réelle (rayon 15 km)
      final results = widget.searchService.searchAroundMe(
        latitude: realPos.latitude,
        longitude: realPos.longitude,
        radiusKm: 15.0,
        limit: 120,
      );

      setState(() {
        _displayedFacilities = results;
        _isLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Position GPS réelle localisée : ${realPos.latitude.toStringAsFixed(4)}°N, ${realPos.longitude.toStringAsFixed(4)}°E (${results.length} fiches à proximité)',
          ),
          duration: const Duration(seconds: 3),
          backgroundColor: Colors.teal.shade800,
        ),
      );
    } else {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Impossible d\'obtenir la position GPS actuelle. Vérifiez les autorisations de localisation.'),
          backgroundColor: Colors.deepOrange,
        ),
      );
    }
  }

  /// Ouvre le sélecteur modal des 58 Wilayas
  Future<void> _openWilayaPicker() async {
    final selected = await WilayaPickerSheet.show(
      context,
      currentCode: _selectedWilayaCode,
    );

    if (!mounted) return;

    if (selected != null) {
      setState(() {
        _selectedWilayaCode = selected.code;
        _selectedWilayaName = selected.name;
        _isLoading = true;
      });

      // 1. Déplacer instantanément la caméra sur le chef-lieu de la wilaya
      final chefLieu = LatLng(selected.lat, selected.lon);
      _mapController.move(chefLieu, 12.0);

      // 2. Filtrer la liste des établissements pour n'afficher que ceux de cette wilaya
      final results = widget.searchService.searchHybrid(
        wilayaCode: selected.code,
        category: _selectedCategory,
        onlyEmergency: _onlyEmergency,
        userLat: _userPosition.latitude,
        userLon: _userPosition.longitude,
        limit: 300,
      );

      setState(() {
        _displayedFacilities = results;
        _isLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Wilaya : ${selected.code} - ${selected.name} (${results.length} fiches chargées)',
          ),
          duration: const Duration(seconds: 3),
          backgroundColor: Colors.teal.shade900,
        ),
      );
    } else {
      // Choix "Tout le pays" / Réinitialisation
      setState(() {
        _selectedWilayaCode = null;
        _selectedWilayaName = null;
        _isLoading = true;
      });

      _zoomToNational();
      _applyFilters();
    }
  }

  void _zoomToNational() {
    _mapController.move(widget.initialCenter, widget.initialZoom);
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
        titleSpacing: 8,
        title: InkWell(
          onTap: _openWilayaPicker,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white24),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  _selectedWilayaCode != null ? Icons.location_on : Icons.public,
                  size: 18,
                  color: Colors.tealAccent.shade100,
                ),
                const SizedBox(width: 6),
                Flexible(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            _selectedWilayaCode != null
                                ? '$_selectedWilayaCode - ${_selectedWilayaName ?? "Wilaya"}'
                                : 'Toute l\'Algérie (58)',
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(width: 4),
                          const Icon(Icons.arrow_drop_down, size: 18, color: Colors.white70),
                        ],
                      ),
                      Text(
                        _selectedWilayaCode != null
                            ? '${_displayedFacilities.length} fiches • Chef-lieu'
                            : '${_displayedFacilities.length} fiches • Hors-ligne',
                        style: const TextStyle(fontSize: 11, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        backgroundColor: Colors.teal.shade800,
        foregroundColor: Colors.white,
        actions: [
          // Bouton sélecteur de Wilaya
          IconButton(
            icon: const Icon(Icons.tune),
            tooltip: 'Sélecteur de Wilaya (58)',
            onPressed: _openWilayaPicker,
          ),
          // Bascule de fond cartographique (OSM / CartoDB Voyager)
          IconButton(
            icon: Icon(_useCartoDb ? Icons.map : Icons.layers_outlined),
            tooltip: _useCartoDb
                ? 'Fond CartoDB Voyager actif (Cliquer pour OSM)'
                : 'Fond OSM Standard actif (Cliquer pour CartoDB)',
            onPressed: () => setState(() => _useCartoDb = !_useCartoDb),
          ),
        ],
      ),
      body: Stack(
        children: [
          // 1. Vue Cartographique flutter_map avec canevas neutre clair médical hors-ligne
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
                  // Gestion gracieuse des erreurs réseau ou hors-ligne
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

              // Marqueur de la position de l'utilisateur
              MarkerLayer(
                markers: [
                  Marker(
                    point: _userPosition,
                    width: 44,
                    height: 44,
                    child: Icon(
                      Icons.my_location,
                      color: _hasRealGps ? Colors.tealAccent.shade400 : Colors.blueGrey.shade400,
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

          // 2. Barre de recherche et filtres de facettes (Wilaya, Catégorie, Urgence)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: FacetFilterBar(
              selectedWilayaCode: _selectedWilayaCode,
              selectedWilayaName: _selectedWilayaName,
              selectedCategory: _selectedCategory,
              onlyEmergency: _onlyEmergency,
              onWilayaChanged: (w) {
                setState(() {
                  _selectedWilayaCode = w;
                  _selectedWilayaName = WilayaInfo.findByCode(w)?.name;
                });
                _applyFilters();
              },
              onWilayaPickerRequested: _openWilayaPicker,
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

          // 4. Boutons d'action flottants (National / Sélecteur Wilaya / Ma Position GPS Réelle)
          Positioned(
            bottom: 24,
            right: 16,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Bouton 1 : Vue Nationale (Tout le pays)
                FloatingActionButton.small(
                  heroTag: 'fab_national',
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.teal.shade800,
                  tooltip: 'Vue Nationale (58 Wilayas)',
                  onPressed: () {
                    setState(() {
                      _selectedWilayaCode = null;
                      _selectedWilayaName = null;
                    });
                    _zoomToNational();
                    _applyFilters();
                  },
                  child: const Icon(Icons.public),
                ),
                const SizedBox(height: 10),
                // Bouton 2 : Sélecteur de Wilaya
                FloatingActionButton.small(
                  heroTag: 'fab_wilaya_selector',
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.teal.shade800,
                  tooltip: 'Choisir une Wilaya (58)',
                  onPressed: _openWilayaPicker,
                  child: const Icon(Icons.location_city),
                ),
                const SizedBox(height: 10),
                // Bouton 3 : Ma Position Réelle GPS
                FloatingActionButton(
                  heroTag: 'fab_my_location',
                  backgroundColor: _hasRealGps ? Colors.teal.shade700 : Colors.teal.shade900,
                  foregroundColor: Colors.white,
                  tooltip: 'Ma position GPS réelle',
                  onPressed: _handleGpsLocationRequest,
                  child: Icon(_hasRealGps ? Icons.my_location : Icons.location_searching),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
