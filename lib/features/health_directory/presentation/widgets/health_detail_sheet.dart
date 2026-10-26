import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/models/crowd_report.dart';
import '../../../../core/models/health_professional.dart';
import '../../../../core/models/pharmacy.dart';
import 'report_anomaly_dialog.dart';

/// Fiche détaillée d'un professionnel ou établissement de santé (Modal BottomSheet)
class HealthDetailSheet extends StatelessWidget {
  final HealthProfessional professional;
  final Future<void> Function(String phoneNumber)? onLaunchCall;
  final Future<void> Function(double lat, double lon)? onLaunchNavigation;
  final bool isFavorite;
  final VoidCallback? onFavoriteToggle;
  final Future<void> Function(CrowdReport report)? onReportSubmitted;

  const HealthDetailSheet({
    super.key,
    required this.professional,
    this.onLaunchCall,
    this.onLaunchNavigation,
    this.isFavorite = false,
    this.onFavoriteToggle,
    this.onReportSubmitted,
  });

  /// Ouvre la modale détaillée de manière ergonomique
  static Future<void> show(
    BuildContext context,
    HealthProfessional professional, {
    Future<void> Function(String phoneNumber)? onLaunchCall,
    Future<void> Function(double lat, double lon)? onLaunchNavigation,
    bool isFavorite = false,
    VoidCallback? onFavoriteToggle,
    Future<void> Function(CrowdReport report)? onReportSubmitted,
  }) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => HealthDetailSheet(
        professional: professional,
        onLaunchCall: onLaunchCall,
        onLaunchNavigation: onLaunchNavigation,
        isFavorite: isFavorite,
        onFavoriteToggle: onFavoriteToggle,
        onReportSubmitted: onReportSubmitted,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isPharma = professional is Pharmacy;
    final isOnDuty = (isPharma && (professional as Pharmacy).isOnDuty) || professional.isEmergency;
    final acceptsChifa = isPharma ? (professional as Pharmacy).acceptsChifa : true;
    final distance = professional.distanceKm;

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 12,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Poignée supérieure ergonomique
          Center(
            child: Container(
              width: 44,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // En-tête : Nom, Catégorie et Bouton Favori
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      professional.nom,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      professional.categorie.toUpperCase(),
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF00695C),
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
              if (onFavoriteToggle != null)
                IconButton(
                  key: const Key('sheet_fav_button'),
                  icon: Icon(
                    isFavorite ? Icons.star : Icons.star_border,
                    color: isFavorite ? Colors.amber.shade700 : Colors.grey.shade400,
                    size: 26,
                  ),
                  tooltip: isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris',
                  onPressed: onFavoriteToggle,
                ),
            ],
          ),
          const SizedBox(height: 12),

          // Badges récapitulatifs (Garde, Chifa, Proximité)
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              if (isOnDuty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFEBEE),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFFC62828)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.alarm, size: 14, color: Color(0xFFC62828)),
                      SizedBox(width: 4),
                      Text(
                        'Service de Garde / Urgences',
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFFB71C1C),
                        ),
                      ),
                    ],
                  ),
                ),
              if (isPharma && acceptsChifa)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE3F2FD),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFF1976D2)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.verified, size: 14, color: Color(0xFF1976D2)),
                      SizedBox(width: 4),
                      Text(
                        'Conventionné Chifa (Tiers-payant)',
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF0D47A1),
                        ),
                      ),
                    ],
                  ),
                ),
              if (distance != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.near_me, size: 14, color: Colors.black87),
                      const SizedBox(width: 4),
                      Text(
                        'À $distance km',
                        style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const Divider(height: 28),

          // Coordonnées administratives & Adresse
          _buildInfoRow(
            icon: Icons.location_on,
            title: 'Adresse & Commune',
            value: professional.adresse != null && professional.adresse!.isNotEmpty
                ? '${professional.adresse}\n${professional.commune}, Wilaya de ${professional.wilaya} (${professional.wilayaCode})'
                : '${professional.commune}, Wilaya de ${professional.wilaya} (${professional.wilayaCode})',
          ),
          const SizedBox(height: 12),

          // Téléphone
          if (professional.telephone != null && professional.telephone!.isNotEmpty) ...[
            _buildInfoRow(
              icon: Icons.phone,
              title: 'Téléphone professionnel',
              value: professional.telephone!,
            ),
            const SizedBox(height: 12),
          ],

          // Position géographique WGS84
          _buildInfoRow(
            icon: Icons.gps_fixed,
            title: 'Coordonnées GPS',
            value: professional.coordinatesFormatted,
          ),
          const SizedBox(height: 20),

          // Actions directes en 1 clic
          Row(
            children: [
              // Bouton 1 : Appel direct
              if (professional.telephone != null && professional.telephone!.isNotEmpty)
                Expanded(
                  child: ElevatedButton.icon(
                    key: const Key('action_call_button'),
                    icon: const Icon(Icons.call, size: 18),
                    label: const Text('Appeler', style: TextStyle(fontWeight: FontWeight.bold)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal.shade800,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    onPressed: () => _handleCall(context),
                  ),
                ),
              if (professional.telephone != null && professional.telephone!.isNotEmpty)
                const SizedBox(width: 10),

              // Bouton 2 : Guidage / Itinéraire GPS
              Expanded(
                child: OutlinedButton.icon(
                  key: const Key('action_nav_button'),
                  icon: const Icon(Icons.directions, size: 18),
                  label: const Text('Itinéraire GPS', style: TextStyle(fontWeight: FontWeight.bold)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.teal.shade900,
                    side: BorderSide(color: Colors.teal.shade800, width: 1.5),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onPressed: () => _handleNavigation(context),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Bouton 3 : Signaler une anomalie
          Center(
            child: TextButton.icon(
              key: const Key('action_report_button'),
              icon: Icon(Icons.report_problem_outlined, size: 16, color: Colors.orange.shade900),
              label: Text(
                'Signaler une anomalie (horaires, fermeture, tél)',
                style: TextStyle(fontSize: 12, color: Colors.orange.shade900),
              ),
              onPressed: () {
                ReportAnomalyDialog.show(
                  context,
                  facility: professional,
                  onSubmit: (report) async {
                    if (onReportSubmitted != null) {
                      await onReportSubmitted!(report);
                    }
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow({
    required IconData icon,
    required String title,
    required String value,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: Colors.teal.shade800),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(fontSize: 11.5, color: Colors.grey, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(fontSize: 13.5, color: Colors.black87),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _handleCall(BuildContext context) async {
    final phone = professional.cleanPhoneNumber;
    if (phone == null || phone.isEmpty) return;

    if (onLaunchCall != null) {
      await onLaunchCall!(phone);
      return;
    }

    final uri = Uri.parse('tel:$phone');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  Future<void> _handleNavigation(BuildContext context) async {
    final lat = professional.latitude;
    final lon = professional.longitude;

    if (onLaunchNavigation != null) {
      await onLaunchNavigation!(lat, lon);
      return;
    }

    final uri = Uri.parse('https://maps.google.com/?q=$lat,$lon');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
