import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';
import '../../../core/models/health_facility.dart';

/// Fiche détaillée d'un établissement de santé avec actions directes (Appel, Guidage, Partage)
class FacilityDetailSheet extends StatelessWidget {
  final HealthFacility facility;

  const FacilityDetailSheet({
    Key? key,
    required this.facility,
  }) : super(key: key);

  static Future<void> show(BuildContext context, HealthFacility facility) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => FacilityDetailSheet(facility: facility),
    );
  }

  Future<void> _makePhoneCall(String phoneNumber) async {
    final Uri launchUri = Uri(
      scheme: 'tel',
      path: phoneNumber,
    );
    if (await canLaunchUrl(launchUri)) {
      await launchUrl(launchUri);
    }
  }

  Future<void> _launchGpsNavigation(double lat, double lon, String label) async {
    // Schéma universel geo: compatible OsmAnd, Organic Maps, Google Maps
    final Uri geoUri = Uri.parse('geo:$lat,$lon?q=$lat,$lon(${Uri.encodeComponent(label)})');
    if (await canLaunchUrl(geoUri)) {
      await launchUrl(geoUri, mode: LaunchMode.externalApplication);
    } else {
      // Fallback web
      final Uri webUri = Uri.parse('https://maps.google.com/?q=$lat,$lon');
      await launchUrl(webUri, mode: LaunchMode.externalApplication);
    }
  }

  void _shareFacility(BuildContext context) {
    Share.share(
      facility.shareText,
      subject: 'Santé DZ : ${facility.nom}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isEmergency = facility.isEmergencyOrOnDuty;

    return Container(
      decoration: BoxDecoration(
        color: theme.scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: const [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 16,
            offset: Offset(0, -4),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Poignée de glissement
          Center(
            child: Container(
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade400,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // En-tête : Nom & Badge d'urgence
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  facility.nom,
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              if (isEmergency)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.red.shade100,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.red.shade400),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.emergency, size: 14, color: Colors.red.shade800),
                      const SizedBox(width: 4),
                      Text(
                        'Urgence / Garde',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: Colors.red.shade900,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),

          // Catégorie et Localisation
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              Chip(
                label: Text(facility.categorie),
                visualDensity: VisualDensity.compact,
                backgroundColor: Colors.teal.shade50,
                labelStyle: TextStyle(color: Colors.teal.shade800, fontSize: 12),
              ),
              Chip(
                label: Text('${facility.commune} (${facility.wilayaCode} - ${facility.wilaya})'),
                visualDensity: VisualDensity.compact,
                backgroundColor: Colors.blue.shade50,
                labelStyle: TextStyle(color: Colors.blue.shade800, fontSize: 12),
              ),
              if (facility.distanceKm != null)
                Chip(
                  avatar: const Icon(Icons.near_me, size: 14, color: Colors.orange),
                  label: Text('${facility.distanceKm} km'),
                  visualDensity: VisualDensity.compact,
                  backgroundColor: Colors.orange.shade50,
                  labelStyle: TextStyle(color: Colors.orange.shade900, fontSize: 12),
                ),
            ],
          ),
          const SizedBox(height: 12),

          // Adresse
          if (facility.adresse != null && facility.adresse!.isNotEmpty) ...[
            Row(
              children: [
                const Icon(Icons.location_on_outlined, size: 18, color: Colors.grey),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    facility.adresse!,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
          ],

          // Coordonnées GPS WGS84
          Row(
            children: [
              const Icon(Icons.gps_fixed, size: 18, color: Colors.grey),
              const SizedBox(width: 8),
              Text(
                'WGS84 : ${facility.wgs84Coordinates}',
                style: theme.textTheme.bodySmall?.copyWith(fontFamily: 'monospace'),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Actions directes (Appel, Itinéraire, Partage)
          Row(
            children: [
              // Appel direct
              if (facility.callNumber != null)
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green.shade600,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.call),
                    label: const Text('Appeler'),
                    onPressed: () => _makePhoneCall(facility.callNumber!),
                  ),
                )
              else
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.phone_disabled, color: Colors.grey),
                    label: const Text('Non renseigné', style: TextStyle(color: Colors.grey)),
                    onPressed: null,
                  ),
                ),
              const SizedBox(width: 10),

              // Guidage GPS hors-ligne
              Expanded(
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.teal.shade700,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  icon: const Icon(Icons.directions),
                  label: const Text('Guidage'),
                  onPressed: () => _launchGpsNavigation(
                    facility.latitude,
                    facility.longitude,
                    facility.nom,
                  ),
                ),
              ),
              const SizedBox(width: 10),

              // Partage
              IconButton.filledTonal(
                icon: const Icon(Icons.share_outlined),
                tooltip: 'Partager',
                onPressed: () => _shareFacility(context),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
