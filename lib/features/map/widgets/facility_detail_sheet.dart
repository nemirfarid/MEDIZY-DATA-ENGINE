import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';
import '../../../core/models/health_facility.dart';
import '../../../core/services/favorites_service.dart';
import '../../../core/services/location_service.dart';
import '../../../core/theme/medizy_theme.dart';
import '../../navigation/presentation/offline_compass_sheet.dart';
import '../../pharma/utils/whatsapp_utils.dart';

/// Fiche détaillée d'un établissement de santé avec actions directes (Appel, Guidage, Partage, Favoris, Boussole)
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
  late final TextEditingController _noteController;
  bool _isNoteSaving = false;

  @override
  void initState() {
    super.initState();
    _noteController = TextEditingController();
    _loadPersonalNote();
    _updateBearingAndDistance();
    // Mise à jour en direct du cap et de la distance toutes les 2 secondes
    _bearingTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      if (mounted) {
        _updateBearingAndDistance();
      }
    });
  }

  Future<void> _loadPersonalNote() async {
    final favService = FavoritesService();
    try {
      await favService.init();
      final note = await favService.getPersonalNote(widget.facility.id);
      if (note != null && note.isNotEmpty && mounted) {
        setState(() {
          _noteController.text = note;
        });
      }
    } catch (_) {}
  }

  Future<void> _savePersonalNote() async {
    setState(() => _isNoteSaving = true);
    final favService = FavoritesService();
    try {
      await favService.init();
      await favService.savePersonalNote(widget.facility.id, _noteController.text);
      if (mounted) {
        setState(() => _isNoteSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Note personnelle enregistrée (stockage 100% privé)'),
            duration: Duration(seconds: 2),
            backgroundColor: MedizyTheme.primary,
          ),
        );
      }
    } catch (_) {
      if (mounted) setState(() => _isNoteSaving = false);
    }
  }

  @override
  void dispose() {
    _bearingTimer?.cancel();
    _noteController.dispose();
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

  String _buildShareText() {
    final sb = StringBuffer();
    sb.writeln('Établissement : ${widget.facility.nom}');
    sb.writeln('Spécialité : ${widget.facility.categorie}');
    sb.writeln('Commune : ${widget.facility.commune}, Wilaya ${widget.facility.wilayaCode} - ${widget.facility.wilaya}');
    sb.writeln('Coordonnées GPS : ${widget.facility.latitude.toStringAsFixed(6)}, ${widget.facility.longitude.toStringAsFixed(6)}');
    sb.writeln('Lien : https://maps.google.com/?q=${widget.facility.latitude},${widget.facility.longitude}');
    if (widget.facility.telephone != null && widget.facility.telephone!.isNotEmpty) {
      sb.writeln('Tél : ${widget.facility.telephone}');
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
      await Share.share(text, subject: 'Santé DZ : ${widget.facility.nom}');
    } catch (_) {
      await Share.share(text, subject: 'Santé DZ : ${widget.facility.nom}');
    }
  }

  Future<void> _copyPhone(BuildContext context) async {
    if (widget.facility.callNumber == null) return;
    await Clipboard.setData(ClipboardData(text: widget.facility.callNumber!));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Numéro copié dans le presse-papier'),
          duration: Duration(seconds: 2),
          backgroundColor: MedizyTheme.primary,
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
          content: Text('Adresse copiée dans le presse-papier'),
          duration: Duration(seconds: 2),
          backgroundColor: MedizyTheme.primary,
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
              isNowFavorite ? 'Ajouté aux favoris' : 'Retiré des favoris',
            ),
            duration: const Duration(seconds: 2),
            backgroundColor: isNowFavorite ? MedizyTheme.accent : Colors.grey,
          ),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Erreur lors de la mise à jour des favoris'),
            duration: Duration(seconds: 2),
            backgroundColor: MedizyTheme.error,
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

  /// Widget boussole compacte et isolée affichant une flèche orientée vers l'établissement
  Widget _buildCompass() {
    return Container(
      width: 76,
      height: 76,
      decoration: BoxDecoration(
        color: MedizyTheme.surface,
        shape: BoxShape.circle,
        border: Border.all(color: MedizyTheme.primary.withValues(alpha: 0.5), width: 2),
        boxShadow: [
          BoxShadow(
            color: MedizyTheme.primaryDark.withValues(alpha: 0.08),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Transform.rotate(
              angle: _bearingDegrees * math.pi / 180,
              child: const Icon(
                Icons.navigation_rounded,
                color: MedizyTheme.primary,
                size: 26,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              '${_bearingDegrees.toStringAsFixed(0)}°',
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 10,
                color: MedizyTheme.primaryDark,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Bouton d'action ergonomique conforme au Design System
  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback? onPressed,
    bool isPrimary = false,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
        child: Container(
          constraints: const BoxConstraints(minHeight: MedizyTheme.minTouchTarget),
          padding: EdgeInsets.symmetric(vertical: MedizyTheme.spacingS, horizontal: MedizyTheme.spacingS),
          decoration: BoxDecoration(
            color: onPressed == null
                ? Colors.grey.shade100
                : (isPrimary ? color : color.withValues(alpha: 0.08)),
            borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
            border: Border.all(
              color: onPressed == null
                  ? Colors.grey.shade300
                  : (isPrimary ? color : color.withValues(alpha: 0.35)),
              width: 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 20,
                color: onPressed == null
                    ? Colors.grey
                    : (isPrimary ? Colors.white : color),
              ),
              const SizedBox(height: 4),
              Text(
                label,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  color: onPressed == null
                      ? Colors.grey
                      : (isPrimary ? Colors.white : color),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isEmergency = widget.facility.isEmergencyOrOnDuty;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      decoration: BoxDecoration(
        color: theme.scaffoldBackgroundColor,
        borderRadius: BorderRadius.vertical(top: Radius.circular(MedizyTheme.borderRadiusL)),
        boxShadow: const [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 16,
            offset: Offset(0, -4),
          ),
        ],
      ),
      padding: EdgeInsets.fromLTRB(MedizyTheme.spacingM, MedizyTheme.spacingS, MedizyTheme.spacingM, MedizyTheme.spacingL + bottomInset),
      child: SingleChildScrollView(
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
            const SizedBox(height: MedizyTheme.spacingM),

            // En-tête : Nom & Badge d'urgence
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    widget.facility.nom,
                    style: theme.textTheme.headlineMedium,
                  ),
                ),
                // Étoile favoris
                FutureBuilder<bool>(
                  future: _isFavorite(),
                  builder: (ctx, snapshot) {
                    final isFav = snapshot.data ?? false;
                    return IconButton(
                      icon: Icon(
                        isFav ? Icons.star : Icons.star_border,
                        color: isFav ? MedizyTheme.accent : Colors.grey,
                        size: 28,
                      ),
                      tooltip: isFav ? 'Retirer des favoris' : 'Ajouter aux favoris',
                      onPressed: () => _toggleFavorite(context),
                    );
                  },
                ),
                if (isEmergency)
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: MedizyTheme.error.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                      border: Border.all(color: MedizyTheme.error),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.emergency, size: 14, color: MedizyTheme.error),
                        SizedBox(width: 4),
                        Text(
                          'Urgence / Garde',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: MedizyTheme.error,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            const SizedBox(height: MedizyTheme.spacingS),

            // Catégorie et Localisation
            Wrap(
              spacing: MedizyTheme.spacingS,
              runSpacing: 4,
              children: [
                Chip(
                  label: Text(widget.facility.categorie),
                  visualDensity: VisualDensity.compact,
                  backgroundColor: MedizyTheme.primary.withValues(alpha: 0.08),
                  labelStyle: const TextStyle(color: MedizyTheme.primary, fontSize: 12),
                ),
                if (widget.facility.hasChifa)
                  Chip(
                    avatar: const Icon(Icons.verified, size: 14, color: Colors.green),
                    label: const Text('CHIFA ✓', style: TextStyle(fontWeight: FontWeight.bold)),
                    visualDensity: VisualDensity.compact,
                    backgroundColor: Colors.green.shade50,
                    labelStyle: TextStyle(color: Colors.green.shade800, fontSize: 12),
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
            const SizedBox(height: MedizyTheme.spacingM),

            // Cap & Distance à vol d'oiseau
            if (_hasPosition || widget.userPosition != null)
              Container(
                padding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: MedizyTheme.primary.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                  border: Border.all(color: MedizyTheme.primary.withValues(alpha: 0.2)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      flex: 1,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.explore_outlined, size: 16, color: MedizyTheme.primary),
                              const SizedBox(width: 6),
                              const Text('Cap direct : ', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                              Text(
                                '${_bearingDegrees.toStringAsFixed(0)}° ${_bearingCardinalDirection()}',
                                style: const TextStyle(fontWeight: FontWeight.bold, color: MedizyTheme.primaryDark, fontSize: 13),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              const Icon(Icons.straighten_outlined, size: 16, color: MedizyTheme.primary),
                              const SizedBox(width: 6),
                              const Text('Distance : ', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                              Text(
                                _hasPosition ? '${_distanceKm.toStringAsFixed(1)} km' : '-- km',
                                style: const TextStyle(fontWeight: FontWeight.bold, color: MedizyTheme.primaryDark, fontSize: 13),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    _buildCompass(),
                  ],
                ),
              ),
            const SizedBox(height: MedizyTheme.spacingM),

            // Adresse
            if (widget.facility.adresse != null && widget.facility.adresse!.isNotEmpty) ...[
              Row(
                children: [
                  const Icon(Icons.location_on_outlined, size: 18, color: MedizyTheme.textSecondary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(widget.facility.adresse!, style: theme.textTheme.bodyMedium),
                  ),
                  IconButton(
                    icon: const Icon(Icons.copy, size: 16, color: MedizyTheme.primary),
                    tooltip: 'Copier l\'adresse',
                    onPressed: () => _copyAddress(context),
                  ),
                ],
              ),
              const SizedBox(height: 4),
            ],

            // Téléphone
            if (widget.facility.telephone != null && widget.facility.telephone!.isNotEmpty) ...[
              Row(
                children: [
                  const Icon(Icons.phone_outlined, size: 18, color: MedizyTheme.textSecondary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      widget.facility.telephone!,
                      style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.copy, size: 16, color: MedizyTheme.primary),
                    tooltip: 'Copier le numéro',
                    onPressed: () => _copyPhone(context),
                  ),
                ],
              ),
              const SizedBox(height: 4),
            ],

            // Coordonnées GPS WGS84
            Row(
              children: [
                const Icon(Icons.gps_fixed, size: 18, color: MedizyTheme.textSecondary),
                const SizedBox(width: 8),
                Text(
                  'WGS84 : ${widget.facility.wgs84Coordinates}',
                  style: theme.textTheme.bodySmall?.copyWith(fontFamily: 'monospace'),
                ),
              ],
            ),
            const SizedBox(height: MedizyTheme.spacingM),

            // Bouton Itinéraire Google Maps (52dp de hauteur)
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                key: const Key('itinerary_google_maps_button'),
                icon: const Icon(Icons.directions_rounded, size: 24, color: Colors.white),
                label: const Text(
                  'Itinéraire Google Maps',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1A73E8),
                  foregroundColor: Colors.white,
                  elevation: 3,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                  ),
                ),
                onPressed: _openGoogleMapsItinerary,
              ),
            ),
            const SizedBox(height: MedizyTheme.spacingM),

            // Grille 2x2 ou Ligne responsive pour les actions secondaires
            LayoutBuilder(
              builder: (context, constraints) {
                final hasWhatsApp = WhatsAppUtils.isAlgerianMobile(widget.facility.telephone);
                return GridView.count(
                  crossAxisCount: hasWhatsApp ? 3 : 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisSpacing: MedizyTheme.spacingS,
                  mainAxisSpacing: MedizyTheme.spacingS,
                  childAspectRatio: 2.2,
                  children: [
                    _buildActionButton(
                      icon: Icons.call,
                      label: 'Appeler',
                      color: Colors.green.shade700,
                      isPrimary: true,
                      onPressed: widget.facility.callNumber != null
                          ? () => _makePhoneCall(widget.facility.callNumber!)
                          : null,
                    ),
                    if (hasWhatsApp)
                      _buildActionButton(
                        icon: Icons.chat_bubble_rounded,
                        label: 'WhatsApp',
                        color: const Color(0xFF25D366),
                        isPrimary: true,
                        onPressed: () => _openWhatsApp(context),
                      ),
                    _buildActionButton(
                      icon: Icons.explore_rounded,
                      label: 'Guidage',
                      color: Colors.blue.shade700,
                      isPrimary: true,
                      onPressed: () {
                        OfflineCompassSheet.show(
                          context,
                          targetName: widget.facility.nom,
                          targetCategory: widget.facility.categorie,
                          targetLat: widget.facility.latitude,
                          targetLon: widget.facility.longitude,
                          userPosition: widget.userPosition,
                        );
                      },
                    ),
                    _buildActionButton(
                      icon: Icons.share_rounded,
                      label: 'Partager',
                      color: Colors.orange.shade800,
                      onPressed: () => _sharePosition(context),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: MedizyTheme.spacingM),

            // Carnet Médical Local Privé & Notes
            Container(
              padding: EdgeInsets.all(MedizyTheme.spacingM),
              decoration: BoxDecoration(
                color: MedizyTheme.surface,
                borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.edit_note, size: 20, color: MedizyTheme.primary),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          'Carnet médical local (Note privée)',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: Colors.grey.shade900,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '100% Privé',
                        style: TextStyle(fontSize: 10, color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                  const SizedBox(height: MedizyTheme.spacingS),
                  TextField(
                    controller: _noteController,
                    maxLines: 2,
                    decoration: InputDecoration(
                      hintText: 'Ex: Secrétaire joignable le matin, Dr reçoit sans RDV...',
                      hintStyle: TextStyle(fontSize: 12, color: Colors.grey.shade400),
                      isDense: true,
                      contentPadding: EdgeInsets.all(10),
                      filled: true,
                      fillColor: Colors.grey.shade50,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                        borderSide: BorderSide(color: Colors.grey.shade300),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                        borderSide: const BorderSide(color: MedizyTheme.primary, width: 1.5),
                      ),
                    ),
                    style: const TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: MedizyTheme.spacingS),
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
                        backgroundColor: MedizyTheme.primary,
                        foregroundColor: Colors.white,
                        visualDensity: VisualDensity.compact,
                        padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openGoogleMapsItinerary() async {
    final destLat = widget.facility.latitude;
    final destLon = widget.facility.longitude;
    final urlStr = 'https://www.google.com/maps/dir/?api=1&destination=$destLat,$destLon&travelmode=driving';
    final uri = Uri.parse(urlStr);
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (_) {}
  }

  Future<void> _openWhatsApp(BuildContext context) async {
    final urlStr = WhatsAppUtils.generateWhatsAppUrl(phone: widget.facility.telephone);
    if (urlStr == null) return;
    final uri = Uri.parse(urlStr);
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (_) {}
  }
}
