import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../../../core/constants/algeria_wilayas.dart';
import '../../../../core/models/health_professional.dart';
import '../../../../core/models/pharmacy.dart';
import '../../../map/utils/specialty_marker_theme.dart';

/// Vue cartographique interactive hors-ligne avec clustering dynamique par Wilaya
/// et Bounding-Box viewport pour assurer 60 FPS sur l'ensemble des 58 Wilayas.
class HealthDirectoryMapView extends StatefulWidget {
  final List<HealthProfessional> facilities;
  final void Function(HealthProfessional) onFacilitySelected;
  final LatLng? initialCenter;
  final double initialZoom;
  final bool enableTiles;
  final String? activeCategory;
  final VoidCallback? onClearCategory;

  const HealthDirectoryMapView({
    super.key,
    required this.facilities,
    required this.onFacilitySelected,
    this.initialCenter,
    this.initialZoom = 11.0,
    this.enableTiles = true,
    this.activeCategory,
    this.onClearCategory,
  });

  @override
  State<HealthDirectoryMapView> createState() => _HealthDirectoryMapViewState();
}

class _HealthDirectoryMapViewState extends State<HealthDirectoryMapView> {
  late final MapController _mapController;
  late double _currentZoom;

  String _getCategoryDisplayName(String? slug) {
    if (slug == null || slug.isEmpty) return '';
    const map = {
      'dentiste': 'Dentistes',
      'pharmacie': 'Pharmacies',
      'laboratoire': 'Laboratoires',
      'imagerie': 'Imagerie & Radio',
      'pédiatre': 'Pédiatres',
      'cardiologue': 'Cardiologues',
      'généraliste': 'Médecins Généralistes',
      'clinique': 'Cliniques & Hôpitaux',
      'gynécologue': 'Gynécologues',
      'ophtalmologue': 'Ophtalmologues',
      'urgences': 'Urgences & Gardes',
    };
    return map[slug.toLowerCase()] ?? (slug[0].toUpperCase() + slug.substring(1));
  }

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
    _currentZoom = widget.initialZoom;
  }

  @override
  Widget build(BuildContext context) {
    // Calcul du centre initial : premier établissement trouvé ou coordonnées d'Alger par défaut
    final center = widget.initialCenter ??
        (widget.facilities.isNotEmpty
            ? LatLng(widget.facilities.first.latitude, widget.facilities.first.longitude)
            : const LatLng(36.7538, 3.0588));

    // Détermination du mode d'affichage selon le niveau de zoom :
    // Zoom < 11.0 : Mode agrégation / clustering par Wilaya (pastille "Nom : Nb")
    // Zoom >= 11.0 : Mode pins individuels avec icônes de spécialités
    final bool isClusterMode = _currentZoom < 11.0 && widget.facilities.length > 25;

    final List<Marker> markers;
    if (isClusterMode) {
      markers = _buildClusterMarkers();
    } else {
      markers = _buildIndividualMarkers();
    }

    final mapWidget = FlutterMap(
      key: const Key('health_directory_flutter_map'),
      mapController: _mapController,
      options: MapOptions(
        initialCenter: center,
        initialZoom: widget.initialZoom,
        minZoom: 4.5,
        maxZoom: 18.0,
        backgroundColor: const Color(0xFFF1F5F7),
        onPositionChanged: (camera, hasGesture) {
          final zoom = camera.zoom;
          if (zoom != null && ((zoom >= 11.0) != (_currentZoom >= 11.0))) {
            setState(() {
              _currentZoom = zoom;
            });
          }
        },
      ),
      children: [
        if (widget.enableTiles)
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'dz.sante.medizy.national',
          ),
        MarkerLayer(
          key: const Key('health_directory_marker_layer'),
          markers: markers,
        ),
      ],
    );

    if (widget.activeCategory == null || widget.activeCategory!.isEmpty) {
      return mapWidget;
    }

    return Stack(
      children: [
        mapWidget,
        Positioned(
          top: 14,
          left: 16,
          child: Material(
            elevation: 4,
            borderRadius: BorderRadius.circular(20),
            color: Colors.white,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.filter_alt, size: 16, color: Colors.teal.shade800),
                  const SizedBox(width: 6),
                  Text(
                    '${_getCategoryDisplayName(widget.activeCategory)} (${widget.facilities.length} résultats)',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Colors.teal.shade900,
                    ),
                  ),
                  if (widget.onClearCategory != null) ...[
                    const SizedBox(width: 8),
                    GestureDetector(
                      key: const Key('clear_directory_category_chip'),
                      onTap: widget.onClearCategory,
                      child: Icon(
                        Icons.cancel,
                        size: 18,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// Construit les marqueurs de cluster par Wilaya à niveau de zoom dézoomé (< 11)
  List<Marker> _buildClusterMarkers() {
    // Regroupement des fiches par code de wilaya
    final Map<String, List<HealthProfessional>> wilayaGroups = {};
    for (final f in widget.facilities) {
      final code = f.wilayaCode.trim().padLeft(2, '0');
      wilayaGroups.putIfAbsent(code, () => []).add(f);
    }

    final clusterMarkers = <Marker>[];

    wilayaGroups.forEach((code, list) {
      final wilayaInfo = WilayaInfo.findByCode(code);
      final count = list.length;
      final wilayaName = wilayaInfo?.name ?? (list.first.wilaya.isNotEmpty ? list.first.wilaya : 'Wilaya $code');

      final LatLng clusterPoint;
      if (wilayaInfo != null) {
        clusterPoint = LatLng(wilayaInfo.lat, wilayaInfo.lon);
      } else {
        // Barycentre moyen des établissements du groupe
        final avgLat = list.fold<double>(0.0, (s, e) => s + e.latitude) / count;
        final avgLon = list.fold<double>(0.0, (s, e) => s + e.longitude) / count;
        clusterPoint = LatLng(avgLat, avgLon);
      }

      clusterMarkers.add(
        Marker(
          key: Key('cluster_marker_$code'),
          point: clusterPoint,
          width: 150,
          height: 38,
          child: GestureDetector(
            onTap: () {
              _mapController.move(clusterPoint, 13.0);
              setState(() {
                _currentZoom = 13.0;
              });
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.teal.shade800,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.white, width: 2),
                boxShadow: const [
                  BoxShadow(
                    color: Colors.black26,
                    blurRadius: 4,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: Center(
                child: Text(
                  '$wilayaName : $count',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
          ),
        ),
      );
    });

    return clusterMarkers;
  }

  /// Construit les pins individuels au zoom local (>= 11) avec limitation Bounding-Box viewport (max 150)
  List<Marker> _buildIndividualMarkers() {
    // Filtrage par Bounding Box visible si la caméra est prête
    List<HealthProfessional> visibleFacilities = widget.facilities;
    try {
      final bounds = _mapController.camera.visibleBounds;
      visibleFacilities = widget.facilities.where((f) {
        return bounds.contains(LatLng(f.latitude, f.longitude));
      }).toList();
    } catch (_) {
      // Fallback si la caméra n'a pas encore calculé son rectangle d'affichage
    }

    // Protection 60 FPS : max 150 marqueurs simultanés
    if (visibleFacilities.length > 150) {
      visibleFacilities = visibleFacilities.sublist(0, 150);
    }

    return visibleFacilities.map((facility) {
      final isOnDuty = (facility is Pharmacy && facility.isOnDuty) || facility.isEmergency;
      final theme = SpecialtyMarkerTheme.forCategory(
        facility.categorie,
        facilityName: facility.nom,
        isEmergency: isOnDuty,
      );

      return Marker(
        key: Key('marker_${facility.id}'),
        point: LatLng(facility.latitude, facility.longitude),
        width: 40,
        height: 40,
        child: GestureDetector(
          onTap: () => widget.onFacilitySelected(facility),
          child: Container(
            decoration: BoxDecoration(
              color: theme.color,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.25),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
              border: Border.all(color: Colors.white, width: 2),
            ),
            child: Icon(
              theme.icon,
              size: 20,
              color: Colors.white,
            ),
          ),
        ),
      );
    }).toList();
  }
}
