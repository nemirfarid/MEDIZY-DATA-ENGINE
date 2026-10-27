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
import '../../navigation/presentation/offline_compass_sheet.dart';

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
          content: Text('Adresse copiée dans le presse-papier'),
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
              isNowFavorite ? 'Ajouté aux favoris' : 'Retiré des favoris',
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
            content: Text('Erreur lors de la mise à jour des favoris'),
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

  /// Widget boussole compacte et isolée affichant une flèche orientée vers l'établissement
  Widget _buildCompass() {
    return Container(
      width: 76,
      height: 76,
      decoration: BoxDecoration(
        color: Colors.white,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.teal.shade300, width: 2),
        boxShadow: [
          BoxShadow(
            color: Colors.teal.shade900.withOpacity(0.08),
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
              child: Icon(
                Icons.navigation_rounded,
                color: Colors.teal.shade800,
                size: 26,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              '${_bearingDegrees.toStringAsFixed(0)}°',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 10,
                color: Colors.teal.shade900,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Bouton d'action uniforme avec icône au-dessus et libellé sans césure
  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback? onPressed,
    bool isPrimary = false,
  }) {
    return Expanded(
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 2),
            decoration: BoxDecoration(
              color: onPressed == null
                  ? Colors.grey.shade100
                  : (isPrimary ? color : color.withOpacity(0.08)),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: onPressed == null
                    ? Colors.grey.shade300
                    : (isPrimary ? color : color.withOpacity(0.35)),
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
                  softWrap: false,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11,
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
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: const [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 16,
            offset: Offset(0, -4),
          ),
        ],
      ),
      padding: EdgeInsets.fromLTRB(20, 12, 20, 24 + bottomInset),
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
          const SizedBox(height: 16),

          // En-tête : Nom & Badge d'urgence
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
              // Étoile favoris
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

          // Catégorie et Localisation
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
          const SizedBox(height: 12),

          // Cap & Distance à vol d'oiseau (Boussole isolée sans chevauchement)
          if (_hasPosition || widget.userPosition != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.teal.shade50.withOpacity(0.7),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.teal.shade200),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  // Bloc gauche : Textes flexibles (Cap, Relèvement, Distance)
                  Expanded(
                    flex: 1,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.explore_outlined, size: 16, color: Colors.teal.shade700),
                            const SizedBox(width: 6),
                            const Text(
                              'Cap direct : ',
                              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                            Text(
                              '${_bearingDegrees.toStringAsFixed(0)}° ${_bearingCardinalDirection()}',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.teal.shade800,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Icon(Icons.straighten_outlined, size: 16, color: Colors.teal.shade700),
                            const SizedBox(width: 6),
                            const Text(
                              'Distance : ',
                              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                            Text(
                              _hasPosition ? '${_distanceKm.toStringAsFixed(1)} km' : '-- km',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.teal.shade800,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Relèvement boussole en direct',
                          style: TextStyle(
                            fontSize: 10,
                            color: Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Bloc droite : Boussole circulaire dédiée sans aucun chevauchement
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
                  icon: const Icon(Icons.copy, size: 16, color: Colors.teal),
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
                const Icon(Icons.phone_outlined, size: 18, color: Colors.grey),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.facility.telephone!,
                    style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.copy, size: 16, color: Colors.teal),
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
              const Icon(Icons.gps_fixed, size: 18, color: Colors.grey),
              const SizedBox(width: 8),
              Text(
                'WGS84 : ${widget.facility.wgs84Coordinates}',
                style: theme.textTheme.bodySmall?.copyWith(fontFamily: 'monospace'),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Actions directes : 4 boutons uniformes, sans retour à la ligne
          Row(
            children: [
              // 1. Appeler
              _buildActionButton(
                icon: Icons.call,
                label: 'Appeler',
                color: Colors.green.shade700,
                isPrimary: true,
                onPressed: widget.facility.callNumber != null
                    ? () => _makePhoneCall(widget.facility.callNumber!)
                    : null,
              ),
              const SizedBox(width: 8),

              // 2. Copier
              _buildActionButton(
                icon: Icons.content_copy_rounded,
                label: 'Copier',
                color: Colors.teal.shade700,
                onPressed: widget.facility.callNumber != null
                    ? () => _copyPhone(context)
                    : null,
              ),
              const SizedBox(width: 8),

              // 3. Guidage (Boussole Hors-ligne & GPS)
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
              const SizedBox(width: 8),

              // 4. Partager pos.
              _buildActionButton(
                icon: Icons.share_rounded,
                label: 'Partager pos.',
                color: Colors.orange.shade800,
                onPressed: () => _sharePosition(context),
              ),
            ],
          ),
          const SizedBox(height: 16),

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
        ],
      ),
      ),
    );
  }
}