import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/models/crowd_report.dart';
import '../../../../core/models/health_professional.dart';
import '../../../../core/models/pharmacy.dart';
import '../../../../core/services/user_storage_service.dart';
import '../../../navigation/presentation/offline_compass_sheet.dart';
import 'report_anomaly_dialog.dart';

/// Fiche détaillée d'un professionnel ou établissement de santé (Modal BottomSheet)
class HealthDetailSheet extends StatefulWidget {
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
  State<HealthDetailSheet> createState() => _HealthDetailSheetState();
}

class _HealthDetailSheetState extends State<HealthDetailSheet> {
  final TextEditingController _noteController = TextEditingController();
  bool _isNoteSaving = false;

  @override
  void initState() {
    super.initState();
    _loadPersonalNote();
  }

  Future<void> _loadPersonalNote() async {
    try {
      final noteRes = await UserStorageService.instance.getPersonalNote(widget.professional.id);
      final noteText = noteRes.dataOrNull;
      if (noteText != null && noteText.isNotEmpty && mounted) {
        setState(() {
          _noteController.text = noteText;
        });
      }
    } catch (_) {}
  }

  Future<void> _savePersonalNote() async {
    setState(() => _isNoteSaving = true);
    try {
      await UserStorageService.instance.savePersonalNote(
        widget.professional.id,
        _noteController.text,
      );
      if (mounted) {
        setState(() => _isNoteSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Note personnelle enregistrée (stockage 100% privé)'),
            duration: Duration(seconds: 2),
            backgroundColor: Colors.teal,
          ),
        );
      }
    } catch (_) {
      if (mounted) setState(() => _isNoteSaving = false);
    }
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final professional = widget.professional;
    final isOnDuty = (professional is Pharmacy && professional.isOnDuty) || professional.isEmergency;
    final acceptsChifa = professional.isChifa;
    final distance = professional.distanceKm;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 12,
        bottom: bottomInset + 24,
      ),
      child: SingleChildScrollView(
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
                if (widget.onFavoriteToggle != null)
                  IconButton(
                    key: const Key('sheet_fav_button'),
                    icon: Icon(
                      widget.isFavorite ? Icons.star : Icons.star_border,
                      color: widget.isFavorite ? Colors.amber.shade700 : Colors.grey.shade400,
                      size: 26,
                    ),
                    tooltip: widget.isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris',
                    onPressed: widget.onFavoriteToggle,
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
                if (acceptsChifa)
                  Container(
                    key: const Key('sheet_badge_chifa'),
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F5E9),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF2E7D32)),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.verified, size: 14, color: Color(0xFF2E7D32)),
                        SizedBox(width: 4),
                        Text(
                          'CHIFA ✓ (Conventionné)',
                          style: TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF1B5E20),
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
            const Divider(height: 24),

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
            const SizedBox(height: 16),

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

                // Bouton 2 : Guidage (Boussole Hors-ligne & GPS)
                Expanded(
                  child: OutlinedButton.icon(
                    key: const Key('action_nav_button'),
                    icon: const Icon(Icons.explore, size: 18),
                    label: const Text('Guidage', style: TextStyle(fontWeight: FontWeight.bold)),
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
            const SizedBox(height: 14),

            // Carnet Médical Local Privé & Notes
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.edit_note, size: 18, color: Colors.teal.shade700),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          'Carnet médical local (Note privée)',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: Colors.teal.shade900,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Stocké localement',
                        style: TextStyle(fontSize: 10, color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _noteController,
                    maxLines: 2,
                    decoration: InputDecoration(
                      hintText: 'Ex: Secrétaire joignable le matin, Dr reçoit sans RDV...',
                      hintStyle: TextStyle(fontSize: 12, color: Colors.grey.shade400),
                      isDense: true,
                      contentPadding: const EdgeInsets.all(10),
                      filled: true,
                      fillColor: Colors.white,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: BorderSide(color: Colors.teal.shade400, width: 1.5),
                      ),
                    ),
                    style: const TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerRight,
                    child: ElevatedButton.icon(
                      onPressed: _isNoteSaving ? null : _savePersonalNote,
                      icon: _isNoteSaving
                          ? const SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(Icons.save_outlined, size: 14),
                      label: const Text('Enregistrer la note', style: TextStyle(fontSize: 11)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.teal,
                        foregroundColor: Colors.white,
                        visualDensity: VisualDensity.compact,
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),

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
                      if (widget.onReportSubmitted != null) {
                        await widget.onReportSubmitted!(report);
                      }
                    },
                  );
                },
              ),
            ),
          ],
        ),
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
    final phone = widget.professional.cleanPhoneNumber;
    if (phone == null || phone.isEmpty) return;

    if (widget.onLaunchCall != null) {
      await widget.onLaunchCall!(phone);
      return;
    }

    final uri = Uri.parse('tel:$phone');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  Future<void> _handleNavigation(BuildContext context) async {
    final lat = widget.professional.latitude;
    final lon = widget.professional.longitude;

    if (widget.onLaunchNavigation != null) {
      await widget.onLaunchNavigation!(lat, lon);
      return;
    }

    OfflineCompassSheet.show(
      context,
      targetName: widget.professional.nom,
      targetCategory: widget.professional.categorie,
      targetLat: lat,
      targetLon: lon,
    );
  }
}
