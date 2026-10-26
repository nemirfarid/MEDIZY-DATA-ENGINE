import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/constants/algeria_wilayas.dart';
import '../../core/models/health_facility.dart';
import '../../core/services/favorites_service.dart';
import '../../core/services/location_service.dart';
import '../../core/services/offline_health_search_service.dart';
import '../../core/services/tile_cache_service.dart';
import 'utils/specialty_marker_theme.dart';
import 'widgets/facility_detail_sheet.dart';
import 'widgets/facet_filter_bar.dart';
import 'widgets/wilaya_picker_sheet.dart';

/// Visualiseur cartographique hors-ligne avec géolocalisation réelle, sélecteur des 58 Wilayas et moteur R-Tree/FTS5
class OfflineMapView extends StatefulWidget {
  final OfflineHealthSearchService searchService;
  final LatLng initialCenter;
  final double initialZoom;
  final String? initialCategory;
  final String? initialWilayaCode;

  const OfflineMapView({
    Key? key,
    required this.searchService,
    this.initialCenter = const LatLng(28.0339, 1.6596), // Centre géographique de l'Algérie
    this.initialZoom = 5.8,
    this.initialCategory,
    this.initialWilayaCode,
  }) : super(key: key);

  @override
  State<OfflineMapView> createState() => _OfflineMapViewState();
}

class _OfflineMapViewState extends State<OfflineMapView> {
  late final MapController _mapController;
  List<HealthFacility> _displayedFacilities = [];
  List<Map<String, dynamic>> _wilayaAggregates = []; // Pastilles d'agrégation par Wilaya
  bool _isLoading = false;
  Timer? _zoomTimer;
  double _currentZoom = 5.8;
  bool _useViewportMode = false; // true = zoom local (viewport), false = vue nationale / agrégation

  String? _selectedWilayaCode;
  String? _selectedWilayaName;
  String? _selectedCategory;
  bool _onlyEmergency = false;
  bool _showChifaOnly = false;
  bool _showFavoritesOnly = false;
  String _currentQuery = '';
  bool _useAltOsmLayer = false;

  // Position utilisateur réelle (par défaut Alger avant détection GPS)
  LatLng _userPosition = LocationService.defaultPosition;
  bool _hasRealGps = false;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _selectedCategory = widget.initialCategory;
    _selectedWilayaCode = widget.initialWilayaCode;
    if (_selectedWilayaCode != null) {
      _selectedWilayaName = WilayaInfo.findByCode(_selectedWilayaCode)?.name;
    }

    _initAppAndLocation();

    // Suivi du niveau de zoom pour basculer entre vue nationale (agrégation Wilaya)
    // et vue locale (markers viewport, max 150).
    _zoomTimer = Timer.periodic(const Duration(milliseconds: 200), (_) {
      if (!mounted) return;
      final currentCameraZoom = _mapController.camera.zoom;
      if (currentCameraZoom == _currentZoom) return;
      setState(() {
        _currentZoom = currentCameraZoom;
        _useViewportMode = currentCameraZoom >= 11.0;
      });
      _applyFilters();
    });
  }

  @override
  void dispose() {
    _zoomTimer?.cancel();
    super.dispose();
  }

  /// Initialisation au démarrage : détection automatique de la Wilaya via GPS,
  /// recentrage intelligent sur la position utilisateur (zoom 13) et chargement des données.
  Future<void> _initAppAndLocation() async {
    setState(() => _isLoading = true);

    try {
      // 1. Initialiser le cache de tuiles disque
      await initTileCache();

      // 2. Détection automatique de position GPS : dernière position connue d'abord (rapide),
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

        // 3. Détection automatique de la Wilaya active à partir des coordonnées GPS si aucune n'est imposée
        if (_selectedWilayaCode == null) {
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
        }

        // 4. Chargement initial en mode viewport (zoom local) depuis la position détectée
        _mapController.move(detectedPos, 13.0);
        _loadViewport();

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Wilaya détectée : $_selectedWilayaCode - $_selectedWilayaName '
                '(${_displayedFacilities.length} fiches à proximité)',
              ),
              duration: const Duration(seconds: 3),
              backgroundColor: Colors.teal.shade800,
            ),
          );
        }
      } else {
        // Pas de GPS : repli propre sur centre par défaut
        _mapController.move(widget.initialCenter, widget.initialZoom);
        if (_showFavoritesOnly) {
          _loadFavorites();
        } else if (_selectedCategory != null || _selectedWilayaCode != null) {
          _applyFilters();
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
  /// Limite stricte de 150 marqueurs pour préserver le thread UI (60 FPS).
  void _loadViewport() {
    final bounds = _mapController.camera.visibleBounds;
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

  /// Charge les établissements favoris sauvegardés.
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

  /// Liste des catégories Conventionné Chifa (pharmacie, laboratoire, imagerie, clinique, hôpital, etc.)
  static const List<String> _chifaCategories = [
    'pharmacie', 'laboratoire', 'centre d\'imagerie médicale', 'centre de radiologie',
    'clinique', 'hôpital', 'polyclinique', 'centre médical', 'centre de santé',
  ];

  /// Retourne la catégorie Chifa correspondante si le filtre Chifa est actif, sinon null.
  String? get _chifaCategory {
    if (!_showChifaOnly) return null;
    // Si une catégorie est déjà sélectionnée et qu'elle est Chifa-compatible, la garder
    if (_selectedCategory != null && _chifaCategories.any((c) => _selectedCategory!.toLowerCase().contains(c.toLowerCase()))) {
      return _selectedCategory;
    }
    // Sinon, on ne filtre pas par catégorie spécifique (tous les Chifa)
    return null;
  }

  /// Indique si le filtre Chifa est actif
  bool get _chifaActive => _showChifaOnly;

  /// Charge les agrégations par Wilaya pour la vue nationale dézoomée (zoom < 11).
  /// Une pastille par wilaya avec le nombre d'établissements (GROUP BY SQL mis en cache).
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

  /// Actualisation des données selon les filtres actifs et le niveau de zoom
  void _applyFilters() {
    setState(() => _isLoading = true);
    try {
      if (_showFavoritesOnly) {
        _loadFavorites();
      } else if (_useViewportMode) {
        // Zoom local : recherche viewport (bounding-box) limitée à 150 marqueurs
        _loadViewport();
      } else if (_selectedWilayaCode == null && _currentQuery.isEmpty && _selectedCategory == null) {
        // Vue nationale dézoomée sans catégorie : agrégation par Wilaya
        _loadWilayaAggregates();
      } else {
        // Filtre wilaya, catégorie ou recherche textuelle : liste complète via searchHybrid
        final results = widget.searchService.searchHybrid(
          query: _currentQuery.isNotEmpty ? _currentQuery : null,
          wilayaCode: _selectedWilayaCode,
          category: _chifaActive ? _chifaCategory : _selectedCategory,
          onlyEmergency: _onlyEmergency,
          userLat: _userPosition.latitude,
          userLon: _userPosition.longitude,
          limit: (_selectedWilayaCode == null && _currentQuery.isEmpty && _selectedCategory == null) ? 50000 : 10000,
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
    final realPos = await LocationService.getCurrentPosition(promptPermission: true);
    if (!mounted) return;

    if (realPos != null) {
      setState(() {
        _userPosition = realPos;
        _hasRealGps = true;
      });

      // Recentrage caméra sur la vraie position (zoom local => mode viewport)
      _mapController.move(realPos, 14.0);

      // Recherche viewport autour de la position réelle (bounding-box, max 150)
      _loadViewport();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Position GPS réelle localisée : ${realPos.latitude.toStringAsFixed(4)}°N, ${realPos.longitude.toStringAsFixed(4)}°E (${_displayedFacilities.length} fiches à proximité)',
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
        _showFavoritesOnly = false;
        _isLoading = true;
      });

      // 1. Déplacer instantanément la caméra sur le chef-lieu de la wilaya (zoom local => viewport)
      final chefLieu = LatLng(selected.lat, selected.lon);
      _mapController.move(chefLieu, 12.0);

      // 2. Filtrer la liste des établissements pour n'afficher que ceux de cette wilaya (viewport)
      _loadViewport();

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Wilaya : ${selected.code} - ${selected.name} (${_displayedFacilities.length} fiches chargées)',
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
        _showFavoritesOnly = false;
        _isLoading = true;
      });

      _zoomToNational();
      _applyFilters();
    }
  }

  /// Pré-télécharge les tuiles OpenStreetMap de la wilaya active pour usage hors-ligne.
  Future<void> _preloadWilayaTiles() async {
    if (_selectedWilayaCode == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Veuillez sélectionner une wilaya d\'abord'),
          duration: Duration(seconds: 2),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      // Récupérer les coordonnées de la wilaya
      final wilaya = WilayaInfo.findByCode(_selectedWilayaCode);
      if (wilaya == null) return;

      // Zone approximative de la wilaya (±1.5° autour du chef-lieu pour couverture large)
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
            content: Text('$count tuiles de la wilaya $_selectedWilayaName mises en cache hors-ligne'),
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
            content: Text('Échec du pré-téléchargement des tuiles'),
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

  SpecialtyMarkerTheme _getTheme(HealthFacility fac) {
    return SpecialtyMarkerTheme.forCategory(
      fac.categorie,
      facilityName: fac.nom,
      isEmergency: fac.isEmergencyOrOnDuty,
    );
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
                            : _showFavoritesOnly
                                ? '${_displayedFacilities.length} favoris'
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
          // Bascule de style cartographique (Standard OSM / Humanitaire HOT OSM)
          IconButton(
            icon: Icon(_useAltOsmLayer ? Icons.map_outlined : Icons.layers_outlined),
            tooltip: _useAltOsmLayer
                ? 'Fond OSM Humanitaire actif (Cliquer pour Standard OSM)'
                : 'Fond OSM Standard actif (Cliquer pour OSM Humanitaire)',
            onPressed: () => setState(() => _useAltOsmLayer = !_useAltOsmLayer),
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
              // Tuiles cartographiques avec cache disque (hors-ligne) et fallback réseau standard OSM
              TileLayer(
                urlTemplate: _useAltOsmLayer
                    ? 'https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png'
                    : 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                fallbackUrl: _useAltOsmLayer
                    ? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
                    : 'https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
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
                  // Fallback automatique sans blocage ni filigrane API key
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

              // Repères des établissements : agrégation par Wilaya (zoom dézoomé < 11)
              // ou markers viewport (zoom local >= 11, max 150 marqueurs) pour 60 FPS
              if (!_useViewportMode && _selectedWilayaCode == null && _currentQuery.isEmpty && _selectedCategory == null && !_showFavoritesOnly)
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
                    final theme = _getTheme(fac);

                    return Marker(
                      point: LatLng(fac.latitude, fac.longitude),
                      width: 40,
                      height: 40,
                      child: GestureDetector(
                        onTap: () => FacilityDetailSheet.show(context, fac, userPosition: _userPosition),
                        child: Container(
                          decoration: BoxDecoration(
                            color: theme.color,
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 2.2),
                            boxShadow: const [
                              BoxShadow(
                                color: Colors.black26,
                                blurRadius: 4,
                                offset: Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Icon(
                            theme.icon,
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

          // 2. Barre de recherche et filtres de facettes (Wilaya, Catégorie, Urgence, Chifa, Favoris)
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

          // 4. Boutons d'action flottants (National / Sélecteur Wilaya / Ma Position GPS Réelle / Précharger tuiles / Urgence)
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
                const SizedBox(height: 10),
                // Bouton 4 : Pré-télécharger tuiles de la wilaya (hors-ligne)
                FloatingActionButton.small(
                  heroTag: 'fab_preload_tiles',
                  backgroundColor: Colors.blue.shade700,
                  foregroundColor: Colors.white,
                  tooltip: 'Pré-télécharger carte wilaya (hors-ligne)',
                  onPressed: _preloadWilayaTiles,
                  child: const Icon(Icons.cloud_download),
                ),
                const SizedBox(height: 10),
                // Bouton 5 : Urgence & Nuit 24/7 (rouge, filtre instantané urgences)
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
