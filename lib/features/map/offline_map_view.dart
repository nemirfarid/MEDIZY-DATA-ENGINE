import '../emergency/presentation/widgets/sos_emergency_sheet.dart';
import '../../core/services/medizy_locale.dart';
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
import '../../core/theme/medizy_theme.dart';
import 'utils/specialty_marker_theme.dart';
import 'widgets/facility_detail_sheet.dart';
import 'widgets/facet_filter_bar.dart';
import 'widgets/wilaya_picker_sheet.dart';
import 'widgets/medizy_map_marker.dart';

/// Visualiseur cartographique Medizy — Google Maps uniquement (Plan + Satellite)
/// Structures de santé uniquement (POI médical), logos Medizy superposés aux coordonnées GPS exactes
class OfflineMapView extends StatefulWidget {
  final OfflineHealthSearchService searchService;
  final LatLng initialCenter;
  final double initialZoom;
  final String? initialCategory;
  final String? initialWilayaCode;

  const OfflineMapView({
    super.key,
    required this.searchService,
    this.initialCenter = const LatLng(28.0339, 1.6596), // Centre géographique de l'Algérie
    this.initialZoom = 5.8,
    this.initialCategory,
    this.initialWilayaCode,
  });

  @override
  State<OfflineMapView> createState() => _OfflineMapViewState();
}

class _OfflineMapViewState extends State<OfflineMapView> {
  late final MapController _mapController;
  List<HealthFacility> _displayedFacilities = [];
  List<Map<String, dynamic>> _wilayaAggregates = [];
  bool _isLoading = false;
  Timer? _zoomTimer;
  double _currentZoom = 5.8;
  bool _useViewportMode = false;
  bool _isNearMeMode = false;
  int _totalCategoryResults = 0;

  String? _selectedWilayaCode;
  String? _selectedWilayaName;
  String? _selectedCommune;
  List<String> _availableCommunes = [];
  String? _selectedCategory;
  bool _onlyEmergency = false;
  bool _showChifaOnly = false;
  bool _showFavoritesOnly = false;
  String _currentQuery = '';

  // Mode de fond de carte : 0 = Google Maps Plan, 1 = Google Maps Satellite
  int _mapLayerMode = 0;

  LatLng _userPosition = LocationService.defaultPosition;
  bool _hasRealGps = false;

  // Suivi des marqueurs sélectionnés pour la fiche détail
  HealthFacility? _selectedFacility;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _selectedCategory = widget.initialCategory;
    _selectedWilayaCode = widget.initialWilayaCode;
    if (_selectedWilayaCode != null) {
      _selectedWilayaName = WilayaInfo.findByCode(_selectedWilayaCode)?.name;
    }

    if (_selectedCategory == null) {
      _initAppAndLocation();
    } else {
      _useViewportMode = true;
      _isLoading = true;
      final results = widget.searchService.searchHybrid(
        category: _selectedCategory,
        limit: 50000,
      );
      setState(() {
        _displayedFacilities = results;
        _totalCategoryResults = results.length;
        _isLoading = false;
      });
    }

    _zoomTimer = Timer.periodic(const Duration(milliseconds: 800), (_) {
      if (!mounted) return;
      final currentCameraZoom = _mapController.camera.zoom;
      if ((currentCameraZoom - _currentZoom).abs() < 0.5) return;
      _currentZoom = currentCameraZoom;
    });
  }

  @override
  void dispose() {
    _zoomTimer?.cancel();
    super.dispose();
  }

  Future<void> _initAppAndLocation() async {
    setState(() => _isLoading = true);

    try {
      await initTileCache();

      LatLng? detectedPos;
      detectedPos = await LocationService.getLastKnownPosition();
      if (detectedPos == null) {
        detectedPos = await LocationService.getCurrentPosition(
          promptPermission: true,
          timeoutSeconds: 6,
        );
      }

      if (detectedPos != null && mounted) {
        _userPosition = detectedPos;
        _hasRealGps = true;

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
              backgroundColor: MedizyTheme.primary,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          );
        }
      } else {
        _mapController.move(widget.initialCenter, widget.initialZoom);
        if (_showFavoritesOnly) {
          _loadFavorites();
        } else if (_selectedCategory != null) {
          _useViewportMode = true;
          final results = widget.searchService.searchHybrid(
            category: _selectedCategory,
            limit: 50000,
          );
          setState(() {
            _displayedFacilities = results;
            _totalCategoryResults = results.length;
            _isLoading = false;
          });
        } else if (_selectedWilayaCode != null) {
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

  static const List<String> _chifaCategories = [
    'pharmacie', 'laboratoire', 'centre d\'imagerie médicale', 'centre de radiologie',
    'clinique', 'hôpital', 'polyclinique', 'centre médical', 'centre de santé',
  ];

  String? get _chifaCategory {
    if (!_showChifaOnly) return null;
    if (_selectedCategory != null && _chifaCategories.any((c) => _selectedCategory!.toLowerCase().contains(c.toLowerCase()))) {
      return _selectedCategory;
    }
    return null;
  }

  bool get _chifaActive => _showChifaOnly;

  void _loadWilayaAggregates() {
    final aggregates = widget.searchService.getWilayaAggregates(
      category: _chifaActive ? _chifaCategory : _selectedCategory,
      onlyEmergency: _onlyEmergency,
    );
    int total = 0;
    for (final agg in aggregates) {
      total += (agg['nb'] as int? ?? 0);
    }
    setState(() {
      _wilayaAggregates = aggregates;
      _totalCategoryResults = total;
      _isLoading = false;
    });
  }

  void _applyFilters() {
    setState(() => _isLoading = true);
    try {
      if (_showFavoritesOnly) {
        _loadFavorites();
      } else if (_selectedCommune != null || _selectedWilayaCode != null || _currentQuery.isNotEmpty) {
        final results = widget.searchService.searchHybrid(
          query: _currentQuery.isNotEmpty ? _currentQuery : null,
          wilayaCode: _selectedWilayaCode,
          commune: _selectedCommune,
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

        if (_currentQuery.isNotEmpty && results.isNotEmpty) {
          final first = results.first;
          _mapController.move(LatLng(first.latitude, first.longitude), 13.0);
        }
      } else if (_useViewportMode) {
        _loadViewport();
      } else {
        _loadWilayaAggregates();
      }
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _handleGpsLocationRequest() async {
    setState(() => _isLoading = true);

    final isEnabled = await LocationService.isServiceEnabled();
    if (!isEnabled && mounted) {
      setState(() => _isLoading = false);
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: Row(
              children: [
                Icon(Icons.location_off, color: MedizyTheme.warning),
                const SizedBox(width: 8),
                Text(MedizyLocale.translateUI('GPS Désactivé')),
              ],
            ),
            content: Text(MedizyLocale.translateUI('Veuillez activer le service de localisation')),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text(MedizyLocale.translateUI('OK')),
              ),
            ],
          ),
        );
      }
      return;
    }

    final realPos = await LocationService.getCurrentPosition(promptPermission: true);
    if (!mounted) return;

    if (realPos != null) {
      setState(() {
        _userPosition = realPos;
        _hasRealGps = true;
        _isNearMeMode = true;
        _selectedWilayaCode = null;
        _selectedWilayaName = null;
        _selectedCommune = null;
        _availableCommunes = [];
        _useViewportMode = true;
      });

      _mapController.move(realPos, 14.5);

      final results = widget.searchService.searchAroundMe(
        latitude: realPos.latitude,
        longitude: realPos.longitude,
        radiusKm: 25.0,
        category: _selectedCategory,
        limit: 250,
      );

      setState(() {
        _displayedFacilities = results;
        _isLoading = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${MedizyLocale.translateUI('Près de moi')} : ${results.length} ${MedizyLocale.translateUI('Structures de santé')}',
            ),
            duration: const Duration(seconds: 3),
            backgroundColor: MedizyTheme.primary,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    } else {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(MedizyLocale.translateUI('Impossible d\'obtenir la position GPS')),
            backgroundColor: MedizyTheme.error,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    }
  }

  Future<void> _openWilayaPicker() async {
    final selected = await WilayaPickerSheet.show(
      context,
      currentCode: _selectedWilayaCode,
    );

    if (!mounted) return;

    if (selected != null) {
      final communes = widget.searchService.getCommunesForWilaya(selected.code);
      setState(() {
        _selectedWilayaCode = selected.code;
        _selectedWilayaName = selected.name;
        _selectedCommune = null;
        _availableCommunes = communes;
        _showFavoritesOnly = false;
        _isLoading = true;
      });

      final chefLieu = LatLng(selected.lat, selected.lon);
      _mapController.move(chefLieu, 12.0);
      _loadViewport();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Wilaya : ${selected.code} - ${selected.name} (${_displayedFacilities.length} ${MedizyLocale.translateUI('Structures de santé')})',
            ),
            duration: const Duration(seconds: 3),
            backgroundColor: MedizyTheme.primaryDark,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
        );
      }
    } else {
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

  void _zoomToNational() {
    _mapController.move(widget.initialCenter, widget.initialZoom);
  }

  void _toggleLanguage() {
    setState(() {
      MedizyLocale.toggleLanguage();
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          MedizyLocale.isArabic
              ? 'اللغة: العربية'
              : 'Langue: Français',
        ),
        duration: const Duration(seconds: 2),
        backgroundColor: MedizyTheme.accent,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }

  void _toggleMapLayer() {
    setState(() {
      _mapLayerMode = (_mapLayerMode + 1) % 2;
    });
    final names = [
      MedizyLocale.t('Google Maps Plan', 'خرائط جوجل - خريطة'),
      MedizyLocale.t('Google Maps Satellite', 'خرائط جوجل - قمر صناعي'),
    ];
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${MedizyLocale.translateUI('Fond de carte')} : ${names[_mapLayerMode]}'),
          duration: const Duration(seconds: 1),
          backgroundColor: MedizyTheme.primary,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
    }
  }

  String _getCategoryDisplayName(String? slug) {
    if (slug == null || slug.isEmpty) return '';
    return MedizyLocale.translateCategory(slug);
  }

  @override
  Widget build(BuildContext context) {
    final isArabic = MedizyLocale.isArabic;

    return Directionality(
      textDirection: isArabic ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        appBar: AppBar(
          titleSpacing: 8,
          title: InkWell(
            onTap: _openWilayaPicker,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white24),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    _selectedWilayaCode != null ? Icons.location_on : Icons.public,
                    size: 18,
                    color: MedizyTheme.accentLight,
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
                            Flexible(
                              child: Text(
                                _selectedWilayaCode != null
                                    ? '$_selectedWilayaCode - ${_selectedWilayaName ?? "Wilaya"}'
                                    : _showFavoritesOnly
                                        ? MedizyLocale.translateUI('Mes Favoris')
                                        : MedizyLocale.t('Toute l\'Algérie (40 752 fiches)', 'كامل الجزائر (40 752 هيكل صحي)'),
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, fontFamily: 'Cairo'),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 4),
                            const Icon(Icons.arrow_drop_down, size: 18, color: Colors.white70),
                          ],
                        ),
                        Text(
                          _selectedWilayaCode != null
                              ? '${_displayedFacilities.length} ${MedizyLocale.translateUI('fiches à proximité')} • ${MedizyLocale.translateUI('Chef-lieu')}'
                              : _showFavoritesOnly
                                  ? '${_displayedFacilities.length} ${MedizyLocale.translateUI('Mes favoris')}'
                                  : '${_displayedFacilities.length > 0 ? _displayedFacilities.length : 40752} ${MedizyLocale.translateUI('Structures de santé')} • 58 ${MedizyLocale.translateUI('Wilayas')}',
                          style: const TextStyle(fontSize: 11, color: Colors.white70, fontFamily: 'Cairo'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          backgroundColor: MedizyTheme.primaryDark,
          foregroundColor: Colors.white,
          actions: [
            // Bouton SOS
            IconButton(
              icon: const Icon(Icons.emergency_rounded, color: Colors.amberAccent, size: 26),
              tooltip: MedizyLocale.t('SOS Urgences 24/7', 'طوارئ صحية 24/7'),
              onPressed: () {
                SosEmergencySheet.show(context, searchService: widget.searchService, userPosition: _userPosition);
              },
            ),
            // Bouton sélecteur Wilaya
            IconButton(
              icon: const Icon(Icons.tune, size: 24),
              tooltip: MedizyLocale.t('Sélecteur de Wilaya (58)', 'اختيار الولاية (58)'),
              onPressed: _openWilayaPicker,
            ),
            // Bouton bascule langue FR/AR
            IconButton(
              icon: Icon(
                isArabic ? Icons.translate_rounded : Icons.language_rounded,
                color: MedizyTheme.accentLight,
                size: 24,
              ),
              tooltip: isArabic
                  ? MedizyLocale.t('Passer au français', 'التبديل إلى الفرنسية')
                  : MedizyLocale.t('Passer en arabe', 'التبديل إلى العربية'),
              onPressed: _toggleLanguage,
            ),
            // Sélecteur de style cartographique (Plan / Satellite)
            IconButton(
              icon: Icon(
                _mapLayerMode == 0 ? Icons.map_rounded : Icons.satellite_alt_rounded,
                color: MedizyTheme.accentLight,
                size: 24,
              ),
              tooltip: _mapLayerMode == 0
                  ? MedizyLocale.t('Google Maps Plan (cliquer pour Satellite)', 'خريطة جوجل (اضغط للقمر الصناعي)')
                  : MedizyLocale.t('Google Maps Satellite (cliquer pour Plan)', 'قمر صناعي جوجل (اضغط للخريطة)'),
              onPressed: _toggleMapLayer,
            ),
          ],
        ),
        body: Stack(
          children: [
            // 1. Carte Google Maps avec tuiles stylisées (POI médical uniquement)
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: widget.initialCenter,
                initialZoom: widget.initialZoom,
                minZoom: 4.5,
                maxZoom: 19.0,
                backgroundColor: MedizyTheme.background,
                onPositionChanged: (camera, hasGesture) {
                  if ((camera.zoom ?? 11.0) >= 11.0) {
                    _loadViewport();
                  }
                },
              ),
              children: [
                // Tuiles Google Maps - Style médical (POI santé uniquement)
                TileLayer(
                  urlTemplate: _mapLayerMode == 0
                      // Google Maps Plan (Roadmap) - POI médical uniquement
                      ? 'https://mt1.google.com/vt/lyrs=m&apistyle=s.t:2|p.v:off,s.t:36|p.v:on&x={x}&y={y}&z={z}'
                      // Google Maps Satellite/Hybrid - POI médical uniquement
                      : 'https://mt1.google.com/vt/lyrs=y&apistyle=s.t:2|p.v:off,s.t:36|p.v:on&x={x}&y={y}&z={z}',
                  fallbackUrl: _mapLayerMode == 0
                      ? 'https://mt0.google.com/vt/lyrs=m&apistyle=s.t:2|p.v:off,s.t:36|p.v:on&x={x}&y={y}&z={z}'
                      : 'https://mt0.google.com/vt/lyrs=y&apistyle=s.t:2|p.v:off,s.t:36|p.v:on&x={x}&y={y}&z={z}',
                  userAgentPackageName: 'dz.sante.medizy.national',
                  additionalOptions: const {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Medizy/1.0',
                  },
                  tileProvider: NetworkTileProvider(
                    headers: {
                      'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Medizy/1.0',
                      'Referer': 'https://medizy.dz',
                    },
                  ),
                  errorTileCallback: (tile, error, stackTrace) {
                    // Silencieux - fallback automatique
                  },
                  tileBuilder: (context, tileWidget, tile) {
                    return Container(
                      decoration: BoxDecoration(
                        border: Border.all(color: MedizyTheme.outlineVariant, width: 0.2),
                      ),
                      child: tileWidget,
                    );
                  },
                ),

                // Marqueur position utilisateur (GPS)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: _userPosition,
                      width: 52,
                      height: 52,
                      child: MedizyUserLocationMarker(
                        hasRealGps: _hasRealGps,
                        size: 52,
                      ),
                    ),
                  ],
                ),

                // Marqueurs : Agrégation Wilaya (zoom < 11, vue nationale)
                if (!_useViewportMode && _selectedWilayaCode == null && _currentQuery.isEmpty && !_showFavoritesOnly)
                  MarkerLayer(
                    markers: _wilayaAggregates.map((agg) {
                      final wilaya = WilayaInfo.findByCode(agg['code'] as String?);
                      if (wilaya == null) return const Marker(point: LatLng(0, 0), width: 0, height: 0, child: SizedBox.shrink());
                      final nb = agg['nb'] as int;
                      final isSelected = _selectedWilayaCode == wilaya.code;
                      return Marker(
                        point: LatLng(wilaya.lat, wilaya.lon),
                        width: 170,
                        height: 48,
                        child: MedizyClusterMarker(
                          wilayaCode: wilaya.code,
                          wilayaName: wilaya.name,
                          count: nb,
                          isSelected: isSelected,
                          onTap: () {
                            _mapController.move(LatLng(wilaya.lat, wilaya.lon), 13.0);
                            setState(() {
                              _selectedWilayaCode = wilaya.code;
                              _selectedWilayaName = wilaya.name;
                              _currentZoom = 13.0;
                              _useViewportMode = true;
                            });
                            _applyFilters();
                          },
                        ),
                      );
                    }).toList(),
                  )
                else
                  // Marqueurs : Structures de santé (viewport zoom >= 11)
                  MarkerLayer(
                    markers: _displayedFacilities.map((fac) {
                      final isSelected = _selectedFacility?.id == fac.id;

                      return Marker(
                        point: LatLng(fac.latitude, fac.longitude),
                        width: 52,
                        height: 52,
                        child: MedizyMapMarker(
                          facility: fac,
                          isSelected: isSelected,
                          isEmergency: fac.isEmergencyOrOnDuty,
                          activeFilterCategory: _selectedCategory,
                          onTap: () {
                            setState(() => _selectedFacility = fac);
                            FacilityDetailSheet.show(context, fac, userPosition: _userPosition);
                          },
                          size: 48,
                        ),
                      );
                    }).toList(),
                  ),
              ],
            ),

            // 2. Barre de recherche et filtres (FacetFilterBar)
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: FacetFilterBar(
                selectedWilayaCode: _selectedWilayaCode,
                selectedWilayaName: _selectedWilayaName,
                selectedCommune: _selectedCommune,
                availableCommunes: _availableCommunes,
                selectedCategory: _selectedCategory,
                onlyEmergency: _onlyEmergency,
                showChifa: _showChifaOnly,
                showFavorites: _showFavoritesOnly,
                isNearMeActive: _isNearMeMode,
                onWilayaChanged: (w) {
                  setState(() {
                    _selectedWilayaCode = w;
                    _selectedWilayaName = WilayaInfo.findByCode(w)?.name;
                    _selectedCommune = null;
                    _availableCommunes = w != null ? widget.searchService.getCommunesForWilaya(w) : [];
                    _isNearMeMode = false;
                    _showFavoritesOnly = false;
                  });
                  _applyFilters();
                },
                onWilayaPickerRequested: () {
                  setState(() => _isNearMeMode = false);
                  _openWilayaPicker();
                },
                onCommuneChanged: (com) {
                  setState(() {
                    _selectedCommune = com;
                    _isNearMeMode = false;
                  });
                  _applyFilters();
                  if (com != null && _displayedFacilities.isNotEmpty) {
                    final f = _displayedFacilities.first;
                    _mapController.move(LatLng(f.latitude, f.longitude), 13.5);
                  }
                },
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
                    _selectedCommune = null;
                    _currentQuery = '';
                    _isNearMeMode = false;
                  }
                  _applyFilters();
                },
                onSearchSubmitted: (q) {
                  setState(() => _currentQuery = q);
                  _applyFilters();
                },
              ),
            ),

            // 2.2. Barre déroulante des Communes
            if (_selectedWilayaCode != null && _availableCommunes.isNotEmpty)
              Positioned(
                top: 104,
                left: 12,
                right: 12,
                child: Container(
                  height: 42,
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: MedizyTheme.shadowS,
                  ),
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    physics: const BouncingScrollPhysics(),
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(right: 6),
                        child: ChoiceChip(
                          label: Text(
                            MedizyLocale.t('Toutes communes', 'كل البلديات'),
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, fontFamily: 'Cairo'),
                          ),
                          selected: _selectedCommune == null,
                          selectedColor: MedizyTheme.primary,
                          labelStyle: TextStyle(
                            color: _selectedCommune == null ? Colors.white : MedizyTheme.primaryDark,
                            fontFamily: 'Cairo',
                          ),
                          onSelected: (selected) {
                            if (selected) {
                              setState(() => _selectedCommune = null);
                              _applyFilters();
                            }
                          },
                        ),
                      ),
                      ..._availableCommunes.map((com) {
                        final isSelected = _selectedCommune == com;
                        return Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: ChoiceChip(
                            label: Text(com, style: const TextStyle(fontSize: 12, fontFamily: 'Cairo')),
                            selected: isSelected,
                            selectedColor: MedizyTheme.primaryLight,
                            labelStyle: TextStyle(
                              color: isSelected ? Colors.white : MedizyTheme.textSecondary,
                              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                              fontFamily: 'Cairo',
                            ),
                            onSelected: (selected) {
                              setState(() => _selectedCommune = selected ? com : null);
                              _applyFilters();
                              if (selected && _displayedFacilities.isNotEmpty) {
                                final f = _displayedFacilities.first;
                                _mapController.move(LatLng(f.latitude, f.longitude), 13.5);
                              }
                            },
                          ),
                        );
                      }).toList(),
                    ],
                  ),
                ),
              ),

            // 2.5. Badge catégorie active
            if (_selectedCategory != null && _selectedCategory!.isNotEmpty)
              Positioned(
                top: _selectedWilayaCode != null && _availableCommunes.isNotEmpty ? 152 : 108,
                left: isArabic ? null : 16,
                right: isArabic ? 16 : null,
                child: Material(
                  elevation: 4,
                  borderRadius: BorderRadius.circular(20),
                  color: Colors.white,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.filter_alt, size: 16, color: MedizyTheme.primary),
                        const SizedBox(width: 6),
                        Text(
                          '${_getCategoryDisplayName(_selectedCategory)} (${_useViewportMode ? _displayedFacilities.length : _totalCategoryResults} ${MedizyLocale.translateUI('résultats')})',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: MedizyTheme.primaryDark,
                            fontFamily: 'Cairo',
                          ),
                        ),
                        const SizedBox(width: 8),
                        GestureDetector(
                          key: const Key('clear_category_chip_button'),
                          onTap: () {
                            setState(() => _selectedCategory = null);
                            _applyFilters();
                          },
                          child: Icon(
                            Icons.remove_circle_outline,
                            size: 18,
                            color: MedizyTheme.textTertiary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

            // 3. Indicateur de chargement
            if (_isLoading)
              Positioned(
                top: 110,
                left: 0,
                right: 0,
                child: Center(
                  child: Card(
                    elevation: 4,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              valueColor: AlwaysStoppedAnimation<Color>(MedizyTheme.primary),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Text(
                            MedizyLocale.t('Recherche locale en cours...', 'جاري البحث المحلي...'),
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              color: MedizyTheme.textPrimary,
                              fontFamily: 'Cairo',
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

            // 4. Boutons d'action flottants (FAB column)
            Positioned(
              bottom: 24,
              right: isArabic ? null : 16,
              left: isArabic ? 16 : null,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Vue Nationale
                  _MedizyFAB(
                    heroTag: 'fab_national',
                    icon: Icons.public_rounded,
                    backgroundColor: Colors.white,
                    foregroundColor: MedizyTheme.primary,
                    tooltip: MedizyLocale.t('Vue Nationale (58 Wilayas)', 'عرض وطني (58 ولاية)'),
                    onPressed: () {
                      setState(() {
                        _selectedWilayaCode = null;
                        _selectedWilayaName = null;
                        _showFavoritesOnly = false;
                      });
                      _zoomToNational();
                      _applyFilters();
                    },
                  ),
                  const SizedBox(height: 10),
                  // Sélecteur Wilaya
                  _MedizyFAB(
                    heroTag: 'fab_wilaya_selector',
                    icon: Icons.location_city_rounded,
                    backgroundColor: Colors.white,
                    foregroundColor: MedizyTheme.primary,
                    tooltip: MedizyLocale.t('Choisir une Wilaya (58)', 'اختيار ولاية (58)'),
                    onPressed: _openWilayaPicker,
                  ),
                  const SizedBox(height: 10),
                  // Ma Position GPS
                  _MedizyFAB(
                    heroTag: 'fab_my_location',
                    icon: _hasRealGps ? Icons.my_location_rounded : Icons.location_searching_rounded,
                    backgroundColor: _hasRealGps ? MedizyTheme.primary : MedizyTheme.primaryDark,
                    foregroundColor: Colors.white,
                    tooltip: MedizyLocale.t('Ma position GPS réelle', 'موقعي الحقيقي GPS'),
                    onPressed: _handleGpsLocationRequest,
                    isLarge: true,
                  ),
                  const SizedBox(height: 10),
                  // Urgence 24/7
                  _MedizyFAB(
                    heroTag: 'fab_emergency',
                    icon: _onlyEmergency ? Icons.emergency_rounded : Icons.warning_amber_rounded,
                    backgroundColor: _onlyEmergency ? MedizyTheme.error : MedizyTheme.error.withValues(alpha: 0.8),
                    foregroundColor: Colors.white,
                    tooltip: MedizyLocale.t('Urgence & Garde 24/7', 'طوارئ ومناوبة 24/7'),
                    onPressed: () {
                      setState(() => _onlyEmergency = !_onlyEmergency);
                      _applyFilters();
                    },
                    isLarge: true,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Bouton FAB stylisé Medizy
class _MedizyFAB extends StatelessWidget {
  final String heroTag;
  final IconData icon;
  final Color backgroundColor;
  final Color foregroundColor;
  final String tooltip;
  final VoidCallback onPressed;
  final bool isLarge;

  const _MedizyFAB({
    required this.heroTag,
    required this.icon,
    required this.backgroundColor,
    required this.foregroundColor,
    required this.tooltip,
    required this.onPressed,
    this.isLarge = false,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: isLarge
          ? FloatingActionButton(
              heroTag: heroTag,
              backgroundColor: backgroundColor,
              foregroundColor: foregroundColor,
              elevation: 6,
              focusElevation: 8,
              hoverElevation: 8,
              highlightElevation: 10,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
              onPressed: onPressed,
              child: Icon(icon, size: 26),
            )
          : FloatingActionButton.small(
              heroTag: heroTag,
              backgroundColor: backgroundColor,
              foregroundColor: foregroundColor,
              elevation: 4,
              focusElevation: 6,
              hoverElevation: 6,
              highlightElevation: 8,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              onPressed: onPressed,
              child: Icon(icon, size: 20),
            ),
    );
  }
}