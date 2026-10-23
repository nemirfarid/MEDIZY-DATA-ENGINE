import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/constants/algeria_wilayas.dart';
import '../../core/models/health_facility.dart';
import '../../core/services/favorites_service.dart';
import '../../core/services/location_service.dart';
import '../../core/services/offline_health_search_service.dart';
import '../../core/services/tile_cache_service.dart';
import 'widgets/facility_detail_sheet.dart';
import 'widgets/facet_filter_bar.dart';
import 'widgets/wilaya_picker_sheet.dart';
import 'dart:async';

/// Visualiseur cartographique hors-ligne avec gÃ©olocalisation rÃ©elle, sÃ©lecteur des 58 Wilayas et moteur R-Tree/FTS5
class OfflineMapView extends StatefulWidget {
  final OfflineHealthSearchService searchService;
  final LatLng initialCenter;
  final double initialZoom;

  const OfflineMapView({
    Key? key,
    required this.searchService,
    this.initialCenter = const LatLng(28.0339, 1.6596), // Centre gÃ©ographique de l'AlgÃ©rie
    this.initialZoom = 5.8,
  }) : super(key: key);

  @override
  State<OfflineMapView> createState() => _OfflineMapViewState();
}

class _OfflineMapViewState extends State<OfflineMapView> {
  late final MapController _mapController;
  List<HealthFacility> _displayedFacilities = [];
  List<Map<String, dynamic>> _wilayaAggregates = []; // Pastilles d'agrÃ©gation par Wilaya
  bool _isLoading = false;
  Timer? _zoomTimer;
  double _currentZoom = 5.8;
  bool _useViewportMode = false; // true = zoom local (viewport), false = vue nationale / agrÃ©gation

  String? _selectedWilayaCode;
  String? _selectedWilayaName;
  String? _selectedCategory;
  bool _onlyEmergency = false;
  bool _showChifaOnly = false;
  bool _showFavoritesOnly = false;
  String _currentQuery = '';
  bool _useCartoDb = false;

  // Position utilisateur rÃ©elle (par dÃ©faut Alger avant dÃ©tection GPS)
  LatLng _userPosition = LocationService.defaultPosition;
  bool _hasRealGps = false;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _initAppAndLocation();
    // Suivi du niveau de zoom pour basculer entre vue nationale (agrÃ©gation Wilaya)
    // et vue locale (markers viewport, max 150).
    _zoomTimer = Timer.periodic(const Duration(milliseconds: 200), (_) {
      if (!mounted || _mapController.zoom == _currentZoom) return;
      final newZoom = _mapController.zoom;
      setState(() {
        _currentZoom = newZoom;
        _useViewportMode = newZoom >= 11.0;
      });
      _applyFilters();
    });
  }

  @override
  void dispose() {
    _zoomTimer?.cancel();
    super.dispose();
  }

  /// Initialisation au dÃ©marrage : dÃ©tection automatique de la Wilaya via GPS,
  /// recentrage intelligent sur la position utilisateur (zoom 13) et chargement des donnÃ©es.
  Future<void> _initAppAndLocation() async {
    setState(() => _isLoading = true);

    try {
      // 1. Initialiser le cache de tuiles disque
      await initTileCache();

      // 2. DÃ©tection automatique de position GPS : derniÃ¨re position connue d'abord (rapide),
      //    puis position actuelle avec timeout court (3s) pour ne pas bloquer l'UI en zone blanche.
      LatLng? detectedPos;
      detectedPos = await LocationService.getLastKnownPosition();
      if (detectedPos == null) {
        detectedPos = await LocationService.getCurrentPosition(
          promptPermission: false,
          timeoutSeconds: 3,
        );
      }

      if (detectedPos != null && mounted) {
        _userPosition = detectedPos;
        _hasRealGps = true;

        // 3. DÃ©tection automatique de la Wilaya active Ã  partir des coordonnÃ©es GPS
        final nearestWilaya = WilayaInfo.findNearestWilaya(
          detectedPos.latitude,
          detectedPos.longitude,
        );
        if (nearestWilaya != null) {
          setState(() {
            _selectedWilayaCode = nearestWilaya.code;
            _selectedWilayaName = nearestWilaya.name;
          });
        }

        // 4. Chargement initial en mode viewport (zoom local) depuis la position dÃ©tectÃ©e
        _mapController.move(detectedPos, 13.0);
        _loadViewport();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Wilaya dÃ©tectÃ©e : $_selectedWilayaCode - $_selectedWilayaName '
                '(${_displayedFacilities.length} fiches Ã  proximitÃ©)',
              ),
              duration: const Duration(seconds: 3),
              backgroundColor: Colors.teal.shade800,
            ),
          );
        }
      } else {
        // Pas de GPS : repli propre sur vue nationale sans popup bloquante
        _mapController.move(widget.initialCenter, widget.initialZoom);
        if (_showFavoritesOnly) {
          _loadFavorites();
        } else {
          _loadWilayaAggregates();
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
        _mapController.move(widget.initialCenter, widget.initialZoom);
        _loadWilayaAggregates();
      }
    }
  }

  /// Charge les marqueurs visibles dans le rectangle courant de la carte (zoom local >= 11).
  /// Limite stricte de 150 marqueurs pour prÃ©server le thread UI (60 FPS).
  void _loadViewport() {
    final bounds = _mapController.bounds!;
    final results = widget.searchService.searchViewport(
      minLat: bounds.southWest.latitude,
      maxLat: bounds.northEast.latitude,
      minLon: bounds.southWest.longitude,
      maxLon: bounds.northEast.longitude,
      category: _chifaActive ? _chifaCategory : _selectedCategory,
      limit: 150,
    );
    setState(() {
      _displayedFacilities = results;
      _isLoading = false;
    });
  }

  /// Charge les Ã©tablissements favoris sauvegardÃ©s.
  void _loadFavorites() async {
    final favService = FavoritesService();
    try {
      await favService.init();
      final rows = await favService.getFavorites();
      final facilities = rows.map((r) => HealthFacility.fromMap({
        'id': r['facility_id'],
        'nom': r['nom'],
        'categorie': r['categorie'],
        'wilaya': r['wilaya'],
        'wilaya_code': r['wilaya_code'],
        'commune': r['commune'],
        'telephone': r['telephone'],
        'adresse': r['adresse'],
        'latitude': r['latitude'],
        'longitude': r['longitude'],
        'source': r['source'],
        'distance_km': r['distance_km'],
      })).toList();
      setState(() {
        _displayedFacilities = facilities;
        _isLoading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  /// Liste des catÃ©gories ConventionnÃ© Chifa (pharmacie, laboratoire, imagerie, clinique, hÃ´pital, etc.)
  static const List<String> _chifaCategories = [
    'pharmacie', 'laboratoire', 'centre d\'imagerie mÃ©dicale', 'centre de radiologie',
    'clinique', 'hÃ´pital', 'polyclinique', 'centre mÃ©dical', 'centre de santÃ©',
  ];

  /// Retourne la catÃ©gorie Chifa correspondante si le filtre Chifa est actif, sinon null.
  String? get _chifaCategory {
    if (!_showChifaOnly) return null;
    // Si une catÃ©gorie est dÃ©jÃ  sÃ©lectionnÃ©e et qu'elle est Chifa-compatible, la garder
    if (_selectedCategory != null && _chifaCategories.any((c) => _selectedCategory!.toLowerCase().contains(c.toLowerCase()))) {
      return _selectedCategory;
    }
    // Sinon, on ne filtre pas par catÃ©gorie spÃ©cifique (tous les Chifa)
    return null;
  }

  /// Indique si le filtre Chifa est actif
  bool get _chifaActive => _showChifaOnly;

  /// Charge les agrÃ©gations par Wilaya pour la vue nationale dÃ©zoomÃ©e (zoom < 11).
  /// Une pastille par wilaya avec le nombre d'Ã©tablissements (GROUP BY SQL mis en cache).
  void _loadWilayaAggregates() {
    final aggregates = widget.searchService.getWilayaAggregates(
      category: _chifaActive ? _chifaCategory : _selectedCategory,
      onlyEmergency: _onlyEmergency,
    );
    setState(() {
      _wilayaAggregates = aggregates;
      _isLoading = false;
    });
  }

  /// Actualisation des donnÃ©es selon les filtres actifs et le niveau de zoom
  void _applyFilters() {
    setState(() => _isLoading = true);
    try {
      if (_showFavoritesOnly) {
        _loadFavorites();
      } else if (_useViewportMode) {
        // Zoom local : recherche viewport (bounding-box) limitÃ©e Ã  150 marqueurs
        _loadViewport();
      } else if (_selectedWilayaCode == null && _currentQuery.isEmpty) {
        // Vue nationale dÃ©zoomÃ©e : agrÃ©gation par Wilaya
        _loadWilayaAggregates();
      } else {
        // Filtre wilaya ou recherche textuelle : liste complÃ¨te via searchHybrid
        final results = widget.searchService.searchHybrid(
          query: _currentQuery.isNotEmpty ? _currentQuery : null,
          wilayaCode: _selectedWilayaCode,
          category: _chifaActive ? _chifaCategory : _selectedCategory,
          onlyEmergency: _onlyEmergency,
          userLat: _userPosition.latitude,
          userLon: _userPosition.longitude,
          limit: (_selectedWilayaCode == null && _currentQuery.isEmpty) ? 50000 : 10000,
        );
        setState(() {
          _displayedFacilities = results;
          _isLoading = false;
        });

        // Si des rÃ©sultats existent et qu'une recherche textuelle vient d'Ãªtre tapÃ©e, centrer sur le premier rÃ©sultat
        if (_currentQuery.isNotEmpty && results.isNotEmpty) {
          final first = results.first;
          _mapController.move(LatLng(first.latitude, first.longitude), 13.0);
        }
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  /// Sollicite activement le capteur GPS du smartphone et recentre la camÃ©ra
  Future<void> _handleGpsLocationRequest() async {
    setState(() => _isLoading = true);

    // 1. VÃ©rification si le service GPS est activÃ© sur l'appareil
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
              Text('GPS DÃ©sactivÃ©'),
            ],
          ),
          content: const Text(
            'Veuillez activer le service de localisation (GPS) dans les paramÃ¨tres de votre tÃ©lÃ©phone pour afficher les Ã©tablissements les plus proches de vous.',
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

    // 2. RÃ©cupÃ©ration de la position GPS prÃ©cise
    final realPos = await LocationService.getCurrentPosition(promptPermission: true);
    if (!mounted) return;

    if (realPos != null) {
      setState(() {
        _userPosition = realPos;
        _hasRealGps = true;
      });

      // Recentrage camÃ©ra sur la vraie position (zoom local => mode viewport)
      _mapController.move(realPos, 14.0);

      // Recherche viewport autour de la position rÃ©elle (bounding-box, max 150)
      _loadViewport();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Position GPS rÃ©elle localisÃ©e : ${realPos.latitude.toStringAsFixed(4)}Â°N, ${realPos.longitude.toStringAsFixed(4)}Â°E (${_displayedFacilities.length} fiches Ã  proximitÃ©)',
          ),
          duration: const Duration(seconds: 3),
          backgroundColor: Colors.teal.shade800,
        ),
      );
    } else {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Impossible d\'obtenir la position GPS actuelle. VÃ©rifiez les autorisations de localisation.'),
          backgroundColor: Colors.deepOrange,
        ),
      );
    }
  }

  /// Ouvre le sÃ©lecteur modal des 58 Wilayas
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
        _showFavoritesOnly = false;
        _isLoading = true;
      });

      // 1. DÃ©placer instantanÃ©ment la camÃ©ra sur le chef-lieu de la wilaya (zoom local => viewport)
      final chefLieu = LatLng(selected.lat, selected.lon);
      _mapController.move(chefLieu, 12.0);

      // 2. Filtrer la liste des Ã©tablissements pour n'afficher que ceux de cette wilaya (viewport)
      _loadViewport();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Wilaya : ${selected.code} - ${selected.name} (${_displayedFacilities.length} fiches chargÃ©es)',
          ),
          duration: const Duration(seconds: 3),
          backgroundColor: Colors.teal.shade900,
        ),
      );
    } else {
      // Choix "Tout le pays" / RÃ©initialisation
      setState(() {
        _selectedWilayaCode = null;
        _selectedWilayaName = null;
        _showFavoritesOnly = false;
        _isLoading = true;
      });

      _zoomToNational();
      _applyFilters();
    }
  }

  /// PrÃ©-tÃ©lÃ©charge les tuiles OpenStreetMap de la wilaya active pour usage hors-ligne.
  Future<void> _preloadWilayaTiles() async {
    if (_selectedWilayaCode == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Veuillez sÃ©lectionner une wilaya d\'abord'),
          duration: Duration(seconds: 2),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      // RÃ©cupÃ©rer les coordonnÃ©es de la wilaya
      final wilaya = WilayaInfo.findByCode(_selectedWilayaCode);
      if (wilaya == null) return;

      // Zone approximative de la wilaya (Â±1.5Â° autour du chef-lieu pour couverture large)
      final margin = 1.5;
      final count = await preloadTilesForBounds(
        minLat: wilaya.lat - margin,
        maxLat: wilaya.lat + margin,
        minLon: wilaya.lon - margin,
        maxLon: wilaya.lon + margin,
        minZoom: 8,
        maxZoom: 13,
        urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      );

      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$count tuiles de la wilaya ${_selectedWilayaName} mises en cache hors-ligne'),
            duration: const Duration(seconds: 3),
            backgroundColor: Colors.teal.shade800,
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Ã‰chec du prÃ©-tÃ©lÃ©chargement des tuiles'),
            duration: Duration(seconds: 3),
            backgroundColor: Colors.red,
          ),
        );
      }
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
                                : _showFavoritesOnly
                                    ? 'Mes Favoris'
                                    : 'Toute l\'AlgÃ©rie (58)',
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(width: 4),
                          const Icon(Icons.arrow_drop_down, size: 18, color: Colors.white70),
                        ],
                      ),
                      Text(
                        _selectedWilayaCode != null
                            ? '${_displayedFacilities.length} fiches â€¢ Chef-lieu'
                            : _showFavoritesOnly
                                ? '${_displayedFacilities.length} favoris'
                                : '${_displayedFacilities.length} fiches â€¢ Hors-ligne',
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
          // Bouton sÃ©lecteur de Wilaya
          IconButton(
            icon: const Icon(Icons.tune),
            tooltip: 'SÃ©lecteur de Wilaya (58)',
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
          // 1. Vue Cartographique flutter_map avec canevas neutre clair mÃ©dical hors-ligne
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: widget.initialCenter,
              initialZoom: widget.initialZoom,
              minZoom: 4.5,
              maxZoom: 18.0,
              backgroundColor: const Color(0xFFEFF3F4), // Fond neutre clair mÃ©dical hors-ligne
            ),
            children: [
              // Tuiles cartographiques avec cache disque (hors-ligne) et fallback rÃ©seau
              TileLayer(
                urlTemplate: _useCartoDb
                    ? 'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png'
                    : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                fallbackUrl: _useCartoDb
                    ? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
                    : 'https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                userAgentPackageName: 'dz.sante.medizy.national',
                additionalOptions: const {
                  'User-Agent': 'Medizy-Algeria/1.0.19 (https://medizy.dz; contact@medizy.dz)',
                },
                tileProvider: NetworkTileProvider(
                  headers: {
                    'User-Agent': 'Medizy-Algeria/1.0.19 (dz.sante.medizy.national)',
                  },
                ),
                errorTileCallback: (tile, error, stackTrace) {
                  // Gestion gracieuse des erreurs rÃ©seau ou hors-ligne
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

              // RepÃ¨res des Ã©tablissements : agrÃ©gation par Wilaya (zoom dÃ©zoomÃ© < 11)
              // ou markers viewport (zoom local >= 11, max 150 marqueurs) pour 60 FPS
              if (!_useViewportMode && _selectedWilayaCode == null && _currentQuery.isEmpty && !_showFavoritesOnly)
                MarkerLayer(
                  markers: _wilayaAggregates.map((agg) {
                    final wilaya = WilayaInfo.findByCode(agg['code'] as String?);
                    if (wilaya == null) return const Marker(point: LatLng(0, 0), width: 0, height: 0, child: SizedBox.shrink());
                    final nb = agg['nb'] as int;
                    return Marker(
                      point: LatLng(wilaya.lat, wilaya.lon),
                      width: 46,
                      height: 46,
                      child: GestureDetector(
                        onTap: () => _openWilayaPicker(),
                        child: Container(
                          decoration: BoxDecoration(
                            color: Colors.teal.shade700,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 3),
                            boxShadow: const [
                              BoxShadow(color: Colors.black26, blurRadius: 6, offset: Offset(0, 3)),
                            ],
                          ),
                          child: Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  nb.toString(),
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 13,
                                  ),
                                ),
                                Text(
                                  agg['code'] as String,
                                  style: const TextStyle(
                                    color: Colors.white70,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 10,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                )
              else
                MarkerLayer(
                  markers: _displayedFacilities.map((fac) {
                    final color = _getMarkerColor(fac);
                    final icon = _getMarkerIcon(fac);

                    return Marker(
                      point: LatLng(fac.latitude, fac.longitude),
                      width: 38,
                      height: 38,
                      child: GestureDetector(
                        onTap: () => FacilityDetailSheet.show(context, fac, userPosition: _userPosition),
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

          // 2. Barre de recherche et filtres de facettes (Wilaya, CatÃ©gorie, Urgence, Chifa, Favoris)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: FacetFilterBar(
              selectedWilayaCode: _selectedWilayaCode,
              selectedWilayaName: _selectedWilayaName,
              selectedCategory: _selectedCategory,
              onlyEmergency: _onlyEmergency,
              showChifa: _showChifaOnly,
              showFavorites: _showFavoritesOnly,
              onWilayaChanged: (w) {
                setState(() {
                  _selectedWilayaCode = w;
                  _selectedWilayaName = WilayaInfo.findByCode(w)?.name;
                  _showFavoritesOnly = false;
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
              onChifaToggled: (chifa) {
                setState(() => _showChifaOnly = chifa);
                _applyFilters();
              },
              onFavoritesToggled: (fav) {
                setState(() => _showFavoritesOnly = fav);
                if (fav) {
                  _selectedWilayaCode = null;
                  _selectedWilayaName = null;
                  _currentQuery = '';
                }
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

          // 4. Boutons d'action flottants (National / SÃ©lecteur Wilaya / Ma Position GPS RÃ©elle / PrÃ©charger tuiles / Urgence)
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
                      _showFavoritesOnly = false;
                    });
                    _zoomToNational();
                    _applyFilters();
                  },
                  child: const Icon(Icons.public),
                ),
                const SizedBox(height: 10),
                // Bouton 2 : SÃ©lecteur de Wilaya
                FloatingActionButton.small(
                  heroTag: 'fab_wilaya_selector',
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.teal.shade800,
                  tooltip: 'Choisir une Wilaya (58)',
                  onPressed: _openWilayaPicker,
                  child: const Icon(Icons.location_city),
                ),
                const SizedBox(height: 10),
                // Bouton 3 : Ma Position RÃ©elle GPS
                FloatingActionButton(
                  heroTag: 'fab_my_location',
                  backgroundColor: _hasRealGps ? Colors.teal.shade700 : Colors.teal.shade900,
                  foregroundColor: Colors.white,
                  tooltip: 'Ma position GPS rÃ©elle',
                  onPressed: _handleGpsLocationRequest,
                  child: Icon(_hasRealGps ? Icons.my_location : Icons.location_searching),
                ),
                const SizedBox(height: 10),
                // Bouton 4 : PrÃ©-tÃ©lÃ©charger tuiles de la wilaya (hors-ligne)
                FloatingActionButton.small(
                  heroTag: 'fab_preload_tiles',
                  backgroundColor: Colors.blue.shade700,
                  foregroundColor: Colors.white,
                  tooltip: 'PrÃ©-tÃ©lÃ©charger carte wilaya (hors-ligne)',
                  onPressed: _preloadWilayaTiles,
                  child: const Icon(Icons.cloud_download),
                ),
                const SizedBox(height: 10),
                // Bouton 5 : Urgence & Nuit 24/7 (rouge, filtre instantanÃ© urgences)
                FloatingActionButton(
                  heroTag: 'fab_emergency',
                  backgroundColor: _onlyEmergency ? Colors.red.shade700 : Colors.red.shade900,
                  foregroundColor: Colors.white,
                  tooltip: 'Urgence & Garde 24/7',
                  onPressed: () {
                    setState(() => _onlyEmergency = !_onlyEmergency);
                    _applyFilters();
                  },
                  child: Icon(_onlyEmergency ? Icons.emergency : Icons.warning_amber),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
