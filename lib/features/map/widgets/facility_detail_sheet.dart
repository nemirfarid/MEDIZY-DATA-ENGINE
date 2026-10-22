import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:share_plus/share_plus.dart';
import '../../../core/models/health_facility.dart';
import '../../../core/services/favorites_service.dart';

/// Fiche détaillée d'un établissement de santé avec actions directes (Appel, Guidage, Partage, Favoris)
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

  /// Génère un texte préformaté prêt à envoyer via WhatsApp/SMS.
  String _buildShareText() {
    final sb = StringBuffer();
    sb.writeln('Établissement : ${facility.nom}');
    sb.writeln('Spécialité : ${facility.categorie}');
    sb.writeln('Commune : ${facility.commune}, Wilaya ${facility.wilayaCode} - ${facility.wilaya}');
    sb.writeln('Coordonnées GPS : ${facility.latitude.toStringAsFixed(6)}, ${facility.longitude.toStringAsFixed(6)}');
    sb.writeln('Lien : https://maps.google.com/?q=${facility.latitude},${facility.longitude}');
    if (facility.telephone != null && facility.telephone!.isNotEmpty) {
      sb.writeln('Tél : ${facility.telephone}');
    }
    return sb.toString();
  }

  /// Partage la position via WhatsApp/SMS (share_plus avec champ SMS).
  Future<void> _sharePosition(BuildContext context) async {
    final text = _buildShareText();
    try {
      // Tentative WhatsApp d'abord (numéro de téléphone cible si disponible)
      if (facility.callNumber != null) {
        final whatsappUri = Uri.parse(
          'whatsapp://send?phone=${facility.callNumber}&text=${Uri.encodeComponent(text)}',
        );
        if (await canLaunchUrl(whatsappUri)) {
          await launchUrl(whatsappUri, mode: LaunchMode.externalApplication);
          return;
        }
      }
      // Fallback : share générique (SMS, email, etc.)
      await Share.share(
        text,
        subject: 'Santé DZ : ${facility.nom}',
      );
    } catch (_) {
      await Share.share(
        text,
        subject: 'Santé DZ : ${facility.nom}',
      );
    }
  }

  /// Copie le numéro de téléphone dans le presse-papier.
  Future<void> _copyPhone(BuildContext context) async {
    if (facility.callNumber == null) return;
    await Clipboard.setData(ClipboardData(text: facility.callNumber!));
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

  /// Copie l'adresse dans le presse-papier.
  Future<void> _copyAddress(BuildContext context) async {
    if (facility.adresse == null || facility.adresse!.isEmpty) return;
    await Clipboard.setData(ClipboardData(text: facility.adresse!));
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

  /// Bascule le statut favori de l'établissement.
  Future<void> _toggleFavorite(BuildContext context) async {
    final favService = FavoritesService();
    try {
      await favService.init();
      final isNowFavorite = await favService.toggleFavorite(
        facilityId: facility.id,
        nom: facility.nom,
        categorie: facility.categorie,
        wilayaCode: facility.wilayaCode,
        wilaya: facility.wilaya,
        commune: facility.commune,
        telephone: facility.telephone,
        adresse: facility.adresse,
        latitude: facility.latitude,
        longitude: facility.longitude,
        source: facility.source,
      );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              isNowFavorite
                  ? 'Ajouté aux favoris'
                  : 'Retiré des favoris',
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

  /// Vérifie si l'établissement est déjà favori.
  Future<bool> _isFavorite() async {
    final favService = FavoritesService();
    try {
      await favService.init();
      return await favService.isFavorite(facility.id);
    } catch (_) {
      return false;
    }
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
                IconButton(
                  icon: const Icon(Icons.content_copy, size: 18, color: Colors.grey),
                  tooltip: 'Copier l\'adresse',
                  onPressed: () => _copyAddress(context),
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

          // Actions directes (Appel, Itinéraire, Partage, Copie)
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
              const SizedBox(width: 8),

              // Copie téléphone
              if (facility.callNumber != null)
                Expanded(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.teal.shade700,
                      side: BorderSide(color: Colors.teal.shade300),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.content_copy, size: 18),
                    label: const Text('Copier Tél', style: TextStyle(fontSize: 11)),
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
                    facility.latitude,
                    facility.longitude,
                    facility.nom,
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
