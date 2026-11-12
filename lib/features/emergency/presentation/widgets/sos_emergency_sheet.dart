import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/models/health_facility.dart';
import '../../../../core/services/location_service.dart';
import '../../../../core/services/offline_health_search_service.dart';
import '../../../../core/theme/medizy_theme.dart';
import '../../../map/widgets/facility_detail_sheet.dart';

/// Feuille modale d'urgence "SOS Santé 24/7" pour l'Algérie (Design Premium)
/// Propose les appels directs (14 Protection Civile, 1548 Police/Urgences)
/// et liste instantanément les structures d'urgence et gardes à proximité.
class SosEmergencySheet extends StatefulWidget {
  final OfflineHealthSearchService searchService;
  final LatLng? userPosition;

  const SosEmergencySheet({
    Key? key,
    required this.searchService,
    this.userPosition,
  }) : super(key: key);

  static Future<void> show(
    BuildContext context, {
    required OfflineHealthSearchService searchService,
    LatLng? userPosition,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => SosEmergencySheet(
        searchService: searchService,
        userPosition: userPosition,
      ),
    );
  }

  @override
  State<SosEmergencySheet> createState() => _SosEmergencySheetState();
}

class _SosEmergencySheetState extends State<SosEmergencySheet> {
  List<HealthFacility> _emergencies = [];
  bool _isLoading = true;
  LatLng _position = LocationService.defaultPosition;

  @override
  void initState() {
    super.initState();
    _loadEmergencies();
  }

  Future<void> _loadEmergencies() async {
    setState(() => _isLoading = true);

    LatLng pos = widget.userPosition ?? _position;
    if (widget.userPosition == null) {
      final detected = await LocationService.getLastKnownPosition();
      if (detected != null) {
        pos = detected;
      }
    }
    _position = pos;

    final results = widget.searchService.searchSosEmergencies(
      latitude: pos.latitude,
      longitude: pos.longitude,
      radiusKm: 10.0,
      limit: 30,
    );

    if (mounted) {
      setState(() {
        _emergencies = results;
        _isLoading = false;
      });
    }
  }

  Future<void> _callNumber(String number) async {
    final uri = Uri(scheme: 'tel', path: number);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.88,
      decoration: const BoxDecoration(
        color: MedizyTheme.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(MedizyTheme.borderRadiusL)),
      ),
      child: Column(
        children: [
          // Poignée supérieure ergonomique
          const SizedBox(height: 12),
          Container(
            width: 48,
            height: 5,
            decoration: BoxDecoration(
              color: Colors.grey.shade300,
              borderRadius: BorderRadius.circular(2.5),
            ),
          ),
          const SizedBox(height: 14),

          // En-tête d'alerte rouge SOS
          Padding(
            padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM),
            child: Row(
              children: [
                Container(
                  padding: EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: MedizyTheme.error.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.emergency,
                    color: MedizyTheme.error,
                    size: 28,
                  ),
                ),
                const SizedBox(width: MedizyTheme.spacingS),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'SOS SANTÉ 24/7',
                        style: TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.bold,
                          color: MedizyTheme.error,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Urgences vitales & Gardes médicales (Algérie)',
                        style: TextStyle(
                          fontSize: 13,
                          color: MedizyTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 24),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
          const SizedBox(height: MedizyTheme.spacingM),

          // 1. BANDEAU DES NUMÉROS D'URGENCE NATIONAUX (14 & 1548)
          Container(
            margin: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM),
            padding: EdgeInsets.all(MedizyTheme.spacingM),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFC62828), Color(0xFFB71C1C)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
              boxShadow: [
                BoxShadow(
                  color: Colors.red.shade300.withValues(alpha: 0.4),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              children: [
                const Row(
                  children: [
                    Icon(Icons.phone_in_talk, color: Colors.white, size: 20),
                    SizedBox(width: 8),
                    Text(
                      'Numéros d\'urgence nationaux gratuits',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: MedizyTheme.spacingM),
                Row(
                  children: [
                    // Bouton 14 - Protection Civile
                    Expanded(
                      child: SizedBox(
                        height: 56,
                        child: ElevatedButton.icon(
                          key: const Key('call_14_button'),
                          onPressed: () => _callNumber('14'),
                          icon: const Icon(Icons.local_fire_department, color: Colors.white, size: 22),
                          label: const Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '14 Protection Civile',
                                style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.white),
                              ),
                              Text(
                                'الحماية المدنية',
                                style: TextStyle(fontSize: 11, color: Colors.white70),
                              ),
                            ],
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white.withValues(alpha: 0.22),
                            foregroundColor: Colors.white,
                            elevation: 0,
                            padding: EdgeInsets.symmetric(horizontal: 10),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                              side: const BorderSide(color: Colors.white60, width: 1.2),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Bouton 1548 - Police Secours
                    Expanded(
                      child: SizedBox(
                        height: 56,
                        child: ElevatedButton.icon(
                          key: const Key('call_1548_button'),
                          onPressed: () => _callNumber('1548'),
                          icon: const Icon(Icons.security, color: Colors.white, size: 22),
                          label: const Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '1548 Police Secours',
                                style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold, color: Colors.white),
                              ),
                              Text(
                                'الشرطة الجزائرية',
                                style: TextStyle(fontSize: 11, color: Colors.white70),
                              ),
                            ],
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white.withValues(alpha: 0.22),
                            foregroundColor: Colors.white,
                            elevation: 0,
                            padding: EdgeInsets.symmetric(horizontal: 10),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                              side: const BorderSide(color: Colors.white60, width: 1.2),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: MedizyTheme.spacingM),

          // 2. LISTE DES ÉTABLISSEMENTS LES PLUS PROCHES (10 KM)
          Padding(
            padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM),
            child: Row(
              children: [
                const Icon(Icons.near_me, size: 18, color: MedizyTheme.primary),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Urgences & Gardes à proximité (Rayon 10 km)',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: MedizyTheme.primary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                if (!_isLoading)
                  Text(
                    '${_emergencies.length} trouvés',
                    style: TextStyle(fontSize: 12, color: MedizyTheme.textSecondary, fontWeight: FontWeight.w500),
                  ),
              ],
            ),
          ),
          const SizedBox(height: MedizyTheme.spacingS),

          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: MedizyTheme.primary))
                : _emergencies.isEmpty
                    ? Center(
                        child: Padding(
                          padding: EdgeInsets.all(MedizyTheme.spacingL),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.location_off_outlined, size: 48, color: MedizyTheme.textSecondary),
                              const SizedBox(height: MedizyTheme.spacingS),
                              const Text(
                                'Aucune structure d\'urgence détectée à moins de 10 km.',
                                textAlign: TextAlign.center,
                                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Contactez immédiatement les secours via le 14 ou le 1548.',
                                textAlign: TextAlign.center,
                                style: TextStyle(color: MedizyTheme.textSecondary, fontSize: 13),
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _emergencies.length,
                        padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM, vertical: 4),
                        itemBuilder: (context, index) {
                          final fac = _emergencies[index];
                          final dist = fac.distanceKm != null
                              ? '${fac.distanceKm} km'
                              : '';

                          return Card(
                            elevation: 1,
                            margin: EdgeInsets.only(bottom: 8),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                              side: BorderSide(color: MedizyTheme.error.withValues(alpha: 0.15)),
                            ),
                            child: ListTile(
                              contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                              onTap: () {
                                Navigator.of(context).pop();
                                FacilityDetailSheet.show(
                                  context,
                                  fac,
                                  userPosition: _position,
                                );
                              },
                              leading: Container(
                                padding: EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: MedizyTheme.error.withValues(alpha: 0.08),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  fac.categorie.toLowerCase().contains('pharmacie')
                                      ? Icons.medication_rounded
                                      : Icons.domain_rounded,
                                  color: MedizyTheme.error,
                                  size: 22,
                                ),
                              ),
                              title: Text(
                                fac.nom,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              subtitle: Text(
                                '${fac.categorie} • ${fac.commune} ($dist)',
                                style: TextStyle(fontSize: 12, color: MedizyTheme.textSecondary),
                              ),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  if (fac.telephone != null && fac.telephone!.isNotEmpty)
                                    IconButton(
                                      icon: const Icon(Icons.phone, color: MedizyTheme.primary),
                                      tooltip: 'Appeler',
                                      onPressed: () {
                                        final num = fac.callNumber ?? fac.telephone!;
                                        _callNumber(num);
                                      },
                                    ),
                                  const Icon(Icons.arrow_forward_ios, size: 14, color: Colors.grey),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
