import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../core/services/location_service.dart';
import '../../../core/utils/geo_calculator.dart';

/// Modal d'orientation boussole et de guidage hors-ligne sans connexion Internet
class OfflineCompassSheet extends StatefulWidget {
  final String facilityName;
  final String category;
  final String locationText;
  final double destinationLatitude;
  final double destinationLongitude;
  final LatLng? initialUserPosition;

  const OfflineCompassSheet({
    Key? key,
    required this.facilityName,
    required this.category,
    required this.locationText,
    required this.destinationLatitude,
    required this.destinationLongitude,
    this.initialUserPosition,
  }) : super(key: key);

  static Future<void> show(
    BuildContext context, {
    String? facilityName,
    String? category,
    String? locationText,
    double? destinationLatitude,
    double? destinationLongitude,
    LatLng? initialUserPosition,
    String? targetName,
    String? targetCategory,
    double? targetLat,
    double? targetLon,
    LatLng? userPosition,
  }) {
    final name = facilityName ?? targetName ?? 'Établissement de santé';
    final cat = category ?? targetCategory ?? 'Santé';
    final loc = locationText ?? '';
    final lat = destinationLatitude ?? targetLat ?? 0.0;
    final lon = destinationLongitude ?? targetLon ?? 0.0;
    final pos = initialUserPosition ?? userPosition;

    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => OfflineCompassSheet(
        facilityName: name,
        category: cat,
        locationText: loc,
        destinationLatitude: lat,
        destinationLongitude: lon,
        initialUserPosition: pos,
      ),
    );
  }

  @override
  State<OfflineCompassSheet> createState() => _OfflineCompassSheetState();
}

class _OfflineCompassSheetState extends State<OfflineCompassSheet> {
  Timer? _refreshTimer;
  LatLng _userPosition = LocationService.defaultPosition;
  double _distanceKm = 0.0;
  double _bearingDegrees = 0.0;
  bool _hasPosition = false;

  @override
  void initState() {
    super.initState();
    if (widget.initialUserPosition != null) {
      _userPosition = widget.initialUserPosition!;
      _hasPosition = true;
    }
    _recalculate();

    // Actualisation de position GPS locale toutes les 2 secondes sans Internet
    _refreshTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      final pos = await LocationService.getCurrentPosition(
        promptPermission: false,
        timeoutSeconds: 2,
      );
      if (pos != null && mounted) {
        setState(() {
          _userPosition = pos;
          _hasPosition = true;
        });
        _recalculate();
      }
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _recalculate() {
    final dist = GeoCalculator.distanceBetween(
      startLatitude: _userPosition.latitude,
      startLongitude: _userPosition.longitude,
      endLatitude: widget.destinationLatitude,
      endLongitude: widget.destinationLongitude,
    );

    final bearing = GeoCalculator.bearingBetween(
      startLatitude: _userPosition.latitude,
      startLongitude: _userPosition.longitude,
      endLatitude: widget.destinationLatitude,
      endLongitude: widget.destinationLongitude,
    );

    setState(() {
      _distanceKm = dist;
      _bearingDegrees = bearing;
    });
  }

  String _formatDistance() {
    if (!_hasPosition) return '-- m';
    final meters = (_distanceKm * 1000).round();
    if (meters < 1000) {
      return '$meters m';
    } else {
      return '${_distanceKm.toStringAsFixed(1)} km';
    }
  }

  Future<void> _launchOnlineMap({bool preferWaze = false}) async {
    final lat = widget.destinationLatitude;
    final lon = widget.destinationLongitude;
    final label = Uri.encodeComponent(widget.facilityName);

    if (preferWaze) {
      final wazeUri = Uri.parse('waze://?ll=$lat,$lon&navigate=yes');
      if (await canLaunchUrl(wazeUri)) {
        await launchUrl(wazeUri, mode: LaunchMode.externalApplication);
        return;
      }
    }

    final geoUri = Uri.parse('geo:$lat,$lon?q=$lat,$lon($label)');
    if (await canLaunchUrl(geoUri)) {
      await launchUrl(geoUri, mode: LaunchMode.externalApplication);
    } else {
      final webUri = Uri.parse('https://maps.google.com/?q=$lat,$lon');
      await launchUrl(webUri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bearingRad = _bearingDegrees * (math.pi / 180.0);
    final cardinal = GeoCalculator.cardinalDirection(_bearingDegrees);

    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.fromLTRB(20, 12, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Poignée supérieure
          Container(
            width: 44,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.grey.shade300,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 14),

          // En-tête
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.teal.shade50,
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.explore, color: Colors.teal.shade800, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.facilityName,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      '${widget.category} • ${widget.locationText}',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const Divider(height: 24),

          // 1. BOUSSOLE HORS-LIGNE AUTONOME
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [const Color(0xFF004D40), Colors.teal.shade800],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(20),
              boxShadow: const [
                BoxShadow(
                  color: Colors.black12,
                  blurRadius: 10,
                  offset: Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              children: [
                const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.offline_pin, color: Colors.tealAccent, size: 16),
                    SizedBox(width: 6),
                    Text(
                      'GUIDAGE 100% HORS-LIGNE (SANS INTERNET)',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 11.5,
                        letterSpacing: 0.6,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Cadran circulaire de boussole avec flèche orientée
                Stack(
                  alignment: Alignment.center,
                  children: [
                    // Cadran de fond
                    Container(
                      width: 140,
                      height: 140,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.teal.shade900.withOpacity(0.5),
                        border: Border.all(color: Colors.tealAccent.withOpacity(0.4), width: 3),
                      ),
                      child: Stack(
                        children: const [
                          Align(
                            alignment: Alignment.topCenter,
                            child: Padding(
                              padding: EdgeInsets.only(top: 4),
                              child: Text('N', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 13)),
                            ),
                          ),
                          Align(
                            alignment: Alignment.bottomCenter,
                            child: Padding(
                              padding: EdgeInsets.only(bottom: 4),
                              child: Text('S', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 11)),
                            ),
                          ),
                          Align(
                            alignment: Alignment.centerRight,
                            child: Padding(
                              padding: EdgeInsets.only(right: 6),
                              child: Text('E', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 11)),
                            ),
                          ),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Padding(
                              padding: EdgeInsets.only(left: 6),
                              child: Text('O', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 11)),
                            ),
                          ),
                        ],
                      ),
                    ),

                    // Aiguille pivotante orientée vers le praticien
                    Transform.rotate(
                      angle: bearingRad,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.navigation,
                            size: 48,
                            color: Colors.tealAccent.shade400,
                          ),
                          const SizedBox(height: 20),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Distance dynamique & Relèvement
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    Column(
                      children: [
                        const Text(
                          'DISTANCE',
                          style: TextStyle(color: Colors.white70, fontSize: 10, letterSpacing: 0.8),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _formatDistance(),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    Container(height: 36, width: 1, color: Colors.white24),
                    Column(
                      children: [
                        const Text(
                          'CAP BOUSSOLE',
                          style: TextStyle(color: Colors.white70, fontSize: 10, letterSpacing: 0.8),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${_bearingDegrees.toStringAsFixed(0)}° $cardinal',
                          style: TextStyle(
                            color: Colors.tealAccent.shade400,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // 2. BOUTONS GOOGLE MAPS / WAZE (EN LIGNE)
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _launchOnlineMap(),
                  icon: const Icon(Icons.map, size: 18),
                  label: const Text('Google Maps'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.teal.shade800,
                    side: BorderSide(color: Colors.teal.shade700),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    padding: EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _launchOnlineMap(preferWaze: true),
                  icon: const Icon(Icons.navigation_outlined, size: 18),
                  label: const Text('Waze GPS'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.indigo.shade800,
                    side: BorderSide(color: Colors.indigo.shade600),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    padding: EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
