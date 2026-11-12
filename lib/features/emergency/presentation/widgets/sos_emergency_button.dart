import '../../../../core/services/medizy_locale.dart';
import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import '../../../../core/services/offline_health_search_service.dart';
import 'sos_emergency_sheet.dart';

/// Bouton d'action flottant distinctif "SOS Santé 24/7" (Rouge médical)
/// Toujours accessible en bas de l'écran pour déclencher en 1 tap l'assistance
/// d'urgence immédiate (14, 1548 et services de garde à moins de 10 km).
class SosEmergencyButton extends StatelessWidget {
  final OfflineHealthSearchService searchService;
  final LatLng? userPosition;

  const SosEmergencyButton({
    Key? key,
    required this.searchService,
    this.userPosition,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: Colors.red.shade900.withOpacity(0.35),
            blurRadius: 10,
            spreadRadius: 1,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: FloatingActionButton.extended(
        key: const Key('sos_emergency_fab'),
        heroTag: 'sos_emergency_fab_tag',
        backgroundColor: const Color(0xFFC62828), // Rouge médical vif
        foregroundColor: Colors.white,
        elevation: 4,
        highlightElevation: 8,
        icon: const Icon(Icons.emergency_rounded, size: 24),
        label: Text(
          MedizyLocale.t('SOS Santé 24/7', 'طوارئ صحية 24/7'),
          style: TextStyle(
            fontWeight: FontWeight.bold,
            letterSpacing: 0.5,
            fontSize: 13,
          ),
        ),
        onPressed: () {
          SosEmergencySheet.show(
            context,
            searchService: searchService,
            userPosition: userPosition,
          );
        },
      ),
    );
  }
}
