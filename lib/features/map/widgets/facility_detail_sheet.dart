import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';
import '../../../core/models/health_facility.dart';
import '../../../core/services/favorites_service.dart';
import '../../../core/services/location_service.dart';

/// Fiche dÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©taillÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e d'un ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tablissement de santÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© avec actions directes (Appel, Guidage, Partage, Favoris, Boussole)
class FacilityDetailSheet extends StatefulWidget {
  final HealthFacility facility;
  final LatLng? userPosition; // Position utilisateur actuelle pour le calcul de cap

  const FacilityDetailSheet({
    Key? key,
    required this.facility,
    this.userPosition,
  }) : super(key: key);

  static Future<void> show(BuildContext context, HealthFacility facility, {LatLng? userPosition}) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => FacilityDetailSheet(facility: facility, userPosition: userPosition),
    );
  }

  @override
  State<FacilityDetailSheet> createState() => _FacilityDetailSheetState();
}

class _FacilityDetailSheetState extends State<FacilityDetailSheet> {
  Timer? _bearingTimer;
  double _distanceKm = 0.0;
  double _bearingDegrees = 0.0;
  bool _hasPosition = false;

  @override
  void initState() {
    super.initState();
    _updateBearingAndDistance();
    // Mise ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  jour en direct du cap et de la distance toutes les 2 secondes
    _bearingTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      if (mounted) {
        _updateBearingAndDistance();
      }
    });
  }

  @override
  void dispose() {
    _bearingTimer?.cancel();
    super.dispose();
  }

  void _updateBearingAndDistance() {
    final userPos = widget.userPosition;
    if (userPos != null) {
      final dist = LocationService.calculateHaversineKm(
        userPos.latitude,
        userPos.longitude,
        widget.facility.latitude,
        widget.facility.longitude,
      );
      final bearing = LocationService.calculateBearingDegrees(
        userPos.latitude,
        userPos.longitude,
        widget.facility.latitude,
        widget.facility.longitude,
      );
      setState(() {
        _distanceKm = dist;
        _bearingDegrees = bearing;
        _hasPosition = true;
      });
    }
  }

  String _bearingCardinalDirection() {
    final idx = ((_bearingDegrees / 22.5).round() + 8) % 16;
    const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO'];
    return directions[idx];
  }

  Future<void> _makePhoneCall(String phoneNumber) async {
    final Uri launchUri = Uri(scheme: 'tel', path: phoneNumber);
    if (await canLaunchUrl(launchUri)) {
      await launchUrl(launchUri);
    }
  }

  Future<void> _launchGpsNavigation(double lat, double lon, String label) async {
    final Uri geoUri = Uri.parse('geo:$lat,$lon?q=$lat,$lon(${Uri.encodeComponent(label)})');
    if (await canLaunchUrl(geoUri)) {
      await launchUrl(geoUri, mode: LaunchMode.externalApplication);
    } else {
      final Uri webUri = Uri.parse('https://maps.google.com/?q=$lat,$lon');
      await launchUrl(webUri, mode: LaunchMode.externalApplication);
    }
  }

  String _buildShareText() {
    final sb = StringBuffer();
    sb.writeln('ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â°tablissement : ${widget.facility.nom}');
    sb.writeln('SpÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©cialitÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© : ${widget.facility.categorie}');
    sb.writeln('Commune : ${widget.facility.commune}, Wilaya ${widget.facility.wilayaCode} - ${widget.facility.wilaya}');
    sb.writeln('CoordonnÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es GPS : ${widget.facility.latitude.toStringAsFixed(6)}, ${widget.facility.longitude.toStringAsFixed(6)}');
    sb.writeln('Lien : https://maps.google.com/?q=${widget.facility.latitude},${widget.facility.longitude}');
    if (widget.facility.telephone != null && widget.facility.telephone!.isNotEmpty) {
      sb.writeln('TÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©l : ${widget.facility.telephone}');
    }
    return sb.toString();
  }

  Future<void> _sharePosition(BuildContext context) async {
    final text = _buildShareText();
    try {
      if (widget.facility.callNumber != null) {
        final whatsappUri = Uri.parse(
          'whatsapp://send?phone=${widget.facility.callNumber}&text=${Uri.encodeComponent(text)}',
        );
        if (await canLaunchUrl(whatsappUri)) {
          await launchUrl(whatsappUri, mode: LaunchMode.externalApplication);
          return;
        }
      }
      await Share.share(text, subject: 'SantÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© DZ : ${widget.facility.nom}');
    } catch (_) {
      await Share.share(text, subject: 'SantÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© DZ : ${widget.facility.nom}');
    }
  }

  Future<void> _copyPhone(BuildContext context) async {
    if (widget.facility.callNumber == null) return;
    await Clipboard.setData(ClipboardData(text: widget.facility.callNumber!));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('NumÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©ro copiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© dans le presse-papier'),
          duration: Duration(seconds: 2),
          backgroundColor: Colors.teal,
        ),
      );
    }
  }

  Future<void> _copyAddress(BuildContext context) async {
    if (widget.facility.adresse == null || widget.facility.adresse!.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: widget.facility.adresse!));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Adresse copiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e dans le presse-papier'),
          duration: Duration(seconds: 2),
          backgroundColor: Colors.teal,
        ),
      );
    }
  }

  Future<void> _toggleFavorite(BuildContext context) async {
    final favService = FavoritesService();
    try {
      await favService.init();
      final isNowFavorite = await favService.toggleFavorite(
        facilityId: widget.facility.id,
        nom: widget.facility.nom,
        categorie: widget.facility.categorie,
        wilayaCode: widget.facility.wilayaCode,
        wilaya: widget.facility.wilaya,
        commune: widget.facility.commune,
        telephone: widget.facility.telephone,
        adresse: widget.facility.adresse,
        latitude: widget.facility.latitude,
        longitude: widget.facility.longitude,
        source: widget.facility.source,
      );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              isNowFavorite ? 'AjoutÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© aux favoris' : 'RetirÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â© des favoris',
            ),
            duration: const Duration(seconds: 2),
            backgroundColor: isNowFavorite ? Colors.amber : Colors.grey,
          ),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Erreur lors de la mise ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  jour des favoris'),
            duration: Duration(seconds: 2),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<bool> _isFavorite() async {
    final favService = FavoritesService();
    try {
      await favService.init();
      return await favService.isFavorite(widget.facility.id);
    } catch (_) {
      return false;
    }
  }

  /// Widget boussole simplifiÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e affichant une flÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨che pointant vers l'ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©tablissement
  Widget _buildCompass() {
    return Container(
      width: 140,
      height: 140,
      decoration: BoxDecoration(
        color: Colors.teal.shade50,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.teal.shade200, width: 2),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // FlÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¨che de direction (boussole)
          Transform.rotate(
            angle: _bearingDegrees * math.pi / 180,
            child: Icon(
              Icons.navigation,
              color: Colors.teal.shade700,
              size: 48,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '${_bearingDegrees.toStringAsFixed(0)}ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â° ${_bearingCardinalDirection()}',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 14,
              color: Colors.teal,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            _hasPosition ? '${_distanceKm.toStringAsFixed(1)} km' : 'ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œ km',
            style: const TextStyle(
              fontSize: 12,
              color: Colors.teal,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Cap direct',
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isEmergency = widget.facility.isEmergencyOrOnDuty;

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
          // PoignÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©e de glissement
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

          // En-tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Âªte : Nom & Badge d'urgence
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  widget.facility.nom,
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              // ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â°toile favoris
              FutureBuilder<bool>(
                future: _isFavorite(),
                builder: (ctx, snapshot) {
                  final isFav = snapshot.data ?? false;
                  return IconButton(
                    icon: Icon(
                      isFav ? Icons.star : Icons.star_border,
                      color: isFav ? Colors.amber : Colors.grey,
                      size: 24,
                    ),
                    tooltip: isFav ? 'Retirer des favoris' : 'Ajouter aux favoris',
                    onPressed: () => _toggleFavorite(context),
                  );
                },
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

          // CatÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©gorie et Localisation
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              Chip(
                label: Text(widget.facility.categorie),
                visualDensity: VisualDensity.compact,
                backgroundColor: Colors.teal.shade50,
                labelStyle: TextStyle(color: Colors.teal.shade800, fontSize: 12),
              ),
              Chip(
                label: Text('${widget.facility.commune} (${widget.facility.wilayaCode} - ${widget.facility.wilaya})'),
                visualDensity: VisualDensity.compact,
                backgroundColor: Colors.blue.shade50,
                labelStyle: TextStyle(color: Colors.blue.shade800, fontSize: 12),
              ),
              if (widget.facility.distanceKm != null)
                Chip(
                  avatar: const Icon(Icons.near_me, size: 14, color: Colors.orange),
                  label: Text('${widget.facility.distanceKm} km'),
                  visualDensity: VisualDensity.compact,
                  backgroundColor: Colors.orange.shade50,
                  labelStyle: TextStyle(color: Colors.orange.shade900, fontSize: 12),
                ),
            ],
          ),
          const SizedBox(height: 12),

          // Cap & Distance ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â  vol d'oiseau (Boussole)
          if (_hasPosition || widget.userPosition != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.teal.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.teal.shade200),
              ),
              child: Row(
                children: [
                  const Icon(Icons.compass_calibration, size: 20, color: Colors.teal),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Row(
                          children: [
                            const Text(
                              'Cap direct : ',
                              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                            Text(
                              '${_bearingDegrees.toStringAsFixed(0)}ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â° ${_bearingCardinalDirection()}',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.teal,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Text(
                              'Distance : ',
                              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                            Text(
                              '${_distanceKm.toStringAsFixed(1)} km',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.teal,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  _buildCompass(),
                ],
              ),
            ),
          const SizedBox(height: 12),

          // Adresse
          if (widget.facility.adresse != null && widget.facility.adresse!.isNotEmpty) ...[
            Row(
              children: [
                const Icon(Icons.location_on_outlined, size: 18, color: Colors.grey),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.facility.adresse!,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.content_copy, size: 18, color: Colors.grey),
                  tooltip: 'Copier l\'adresse',
                  onPressed: () => _copyAddress(context),
                ),
              ],
            ),
            const SizedBox(height: 8),
          ],

          // CoordonnÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©es GPS WGS84
          Row(
            children: [
              const Icon(Icons.gps_fixed, size: 18, color: Colors.grey),
              const SizedBox(width: 8),
              Text(
                'WGS84 : ${widget.facility.wgs84Coordinates}',
                style: theme.textTheme.bodySmall?.copyWith(fontFamily: 'monospace'),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Actions directes (Appel, ItinÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©raire, Partage, Copie)
          Row(
            children: [
              // Appel direct
              if (widget.facility.callNumber != null)
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
                    onPressed: () => _makePhoneCall(widget.facility.callNumber!),
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
                    label: const Text('Non renseignÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©', style: TextStyle(color: Colors.grey)),
                    onPressed: null,
                  ),
                ),
              const SizedBox(width: 8),

              // Copie tÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©lÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©phone
              if (widget.facility.callNumber != null)
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.teal.shade700,
                      side: BorderSide(color: Colors.teal.shade300),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.content_copy, size: 18),
                    label: const Text('Copier TÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â©l', style: TextStyle(fontSize: 11)),
                    onPressed: () => _copyPhone(context),
                  ),
                )
              else
                const SizedBox(width: 0),

              const SizedBox(width: 8),

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
                    widget.facility.latitude,
                    widget.facility.longitude,
                    widget.facility.nom,
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // Partage position (WhatsApp/SMS)
              Expanded(
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.green.shade700,
                    side: BorderSide(color: Colors.green.shade300),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  icon: const Icon(Icons.share_outlined, size: 18),
                  label: const Text('Partager pos.', style: TextStyle(fontSize: 11)),
                  onPressed: () => _sharePosition(context),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}