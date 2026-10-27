import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/models/health_facility.dart';
import '../../../../core/services/location_service.dart';
import '../../../../core/services/offline_health_search_service.dart';
import '../../../map/widgets/facility_detail_sheet.dart';

/// Feuille modale d'urgence "SOS Santé 24/7" pour l'Algérie
/// Propose les appels directs (14 Protection Civile, 1548 Police/Urgences)
/// et liste instantanément les structures d'urgence et gardes à moins de 10 km.
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
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Poignée supérieure
          const SizedBox(height: 12),
          Container(
            width: 44,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.grey.shade300,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 14),

          // En-tête d'alerte rouge SOS
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.red.shade100,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.emergency,
                    color: Colors.red.shade800,
                    size: 26,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'SOS SANTÉ 24/7',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Colors.red.shade900,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Urgences vitales & Gardes médicales (Algérie)',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // 1. BANDEAU DES NUMÉROS D'URGENCE NATIONAUX (14 & 1548)
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Colors.red.shade800, Colors.red.shade900],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.red.shade300.withOpacity(0.5),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              children: [
                const Row(
                  children: [
                    Icon(Icons.phone_in_talk, color: Colors.white, size: 18),
                    SizedBox(width: 8),
                    Text(
                      'Numéros d\'urgence nationaux gratuits',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    // Bouton 14 - Protection Civile
                    Expanded(
                      child: ElevatedButton.icon(
                        key: const Key('call_14_button'),
                        onPressed: () => _callNumber('14'),
                        icon: const Icon(Icons.local_fire_department, color: Colors.white, size: 18),
                        label: const Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '14 Protection Civile',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                            ),
                            Text(
                              'الحماية المدنية',
                              style: TextStyle(fontSize: 10, color: Colors.white70),
                            ),
                          ],
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white.withOpacity(0.2),
                          foregroundColor: Colors.white,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                            side: const BorderSide(color: Colors.white54, width: 1),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Bouton 1548 - Police Secours
                    Expanded(
                      child: ElevatedButton.icon(
                        key: const Key('call_1548_button'),
                        onPressed: () => _callNumber('1548'),
                        icon: const Icon(Icons.security, color: Colors.white, size: 18),
                        label: const Column(
                          mainAxisSize: MainAxisSize.min,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '1548 Police Secours',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                            ),
                            Text(
                              'الشرطة الجزائرية',
                              style: TextStyle(fontSize: 10, color: Colors.white70),
                            ),
                          ],
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white.withOpacity(0.2),
                          foregroundColor: Colors.white,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                            side: const BorderSide(color: Colors.white54, width: 1),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // 2. LISTE DES ÉTABLISSEMENTS LES PLUS PROCHES (10 KM)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: [
                Icon(Icons.near_me, size: 16, color: Colors.teal.shade800),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Urgences & Gardes à proximité (Rayon 10 km)',
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.bold,
                      color: Colors.teal.shade900,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                if (!_isLoading)
                  Text(
                    '${_emergencies.length} trouvés',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _emergencies.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24.0),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.location_off_outlined, size: 48, color: Colors.grey.shade400),
                              const SizedBox(height: 12),
                              const Text(
                                'Aucune structure d\'urgence détectée à moins de 10 km.',
                                textAlign: TextAlign.center,
                                style: TextStyle(fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'Contactez immédiatement les secours via le 14 ou le 1548.',
                                textAlign: TextAlign.center,
                                style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                              ),
                            ],
                          ),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _emergencies.length,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        itemBuilder: (context, index) {
                          final fac = _emergencies[index];
                          final dist = fac.distanceKm != null
                              ? '${fac.distanceKm} km'
                              : '';

                          return Card(
                            margin: const EdgeInsets.only(bottom: 8),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                              side: BorderSide(color: Colors.red.shade100),
                            ),
                            child: ListTile(
                              leading: Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: Colors.red.shade50,
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(
                                  fac.categorie.toLowerCase().contains('pharmacie')
                                      ? Icons.local_pharmacy
                                      : Icons.local_hospital,
                                  color: Colors.red.shade800,
                                  size: 20,
                                ),
                              ),
                              title: Text(
                                fac.nom,
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13.5),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              subtitle: Text(
                                '${fac.categorie} • ${fac.commune} ($dist)',
                                style: TextStyle(fontSize: 11.5, color: Colors.grey.shade700),
                              ),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  if (fac.telephone != null && fac.telephone!.isNotEmpty)
                                    IconButton(
                                      icon: const Icon(Icons.phone, color: Colors.teal),
                                      tooltip: 'Appeler',
                                      onPressed: () {
                                        final num = fac.callNumber ?? fac.telephone!;
                                        _callNumber(num);
                                      },
                                    ),
                                  IconButton(
                                    icon: const Icon(Icons.arrow_forward_ios, size: 14),
                                    onPressed: () {
                                      Navigator.of(context).pop();
                                      FacilityDetailSheet.show(
                                        context,
                                        fac,
                                        userPosition: _position,
                                      );
                                    },
                                  ),
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
