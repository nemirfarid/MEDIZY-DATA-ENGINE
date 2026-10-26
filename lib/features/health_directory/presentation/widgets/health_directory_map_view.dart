import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../../../core/models/health_professional.dart';
import '../../../../core/models/pharmacy.dart';

import '../../../map/utils/specialty_marker_theme.dart';

/// Vue cartographique interactive hors-ligne affichant les établissements de santé
class HealthDirectoryMapView extends StatelessWidget {
  final List<HealthProfessional> facilities;
  final void Function(HealthProfessional) onFacilitySelected;
  final LatLng? initialCenter;
  final double initialZoom;
  final bool enableTiles;

  const HealthDirectoryMapView({
    super.key,
    required this.facilities,
    required this.onFacilitySelected,
    this.initialCenter,
    this.initialZoom = 11.0,
    this.enableTiles = true,
  });

  @override
  Widget build(BuildContext context) {
    // Calcul du centre initial : premier établissement trouvé ou coordonnées d'Alger par défaut
    final center = initialCenter ??
        (facilities.isNotEmpty
            ? LatLng(facilities.first.latitude, facilities.first.longitude)
            : const LatLng(36.7538, 3.0588));

    return FlutterMap(
      key: const Key('health_directory_flutter_map'),
      options: MapOptions(
        initialCenter: center,
        initialZoom: initialZoom,
        minZoom: 4.5,
        maxZoom: 18.0,
        backgroundColor: const Color(0xFFF1F5F7),
      ),
      children: [
        if (enableTiles)
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'dz.sante.medizy.national',
          ),
        MarkerLayer(
          markers: facilities.map((facility) {
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
                onTap: () => onFacilitySelected(facility),
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
          }).toList(),
        ),
      ],
    );
  }
}
