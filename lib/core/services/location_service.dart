import 'dart:math' as math;

import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Service de gestion de la géolocalisation réelle du terminal (GPS)
class LocationService {
  // Position par défaut (Alger Centre) utilisée uniquement en cas d'absence totale de capteur
  static const LatLng defaultPosition = LatLng(36.7538, 3.0588);

  /// Vérifie si le service GPS est activé sur le terminal
  static Future<bool> isServiceEnabled() async {
    try {
      return await Geolocator.isLocationServiceEnabled();
    } catch (_) {
      return false;
    }
  }

  /// Récupère la dernière position GPS connue du terminal (cache système, très rapide)
  static Future<LatLng?> getLastKnownPosition() async {
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return null;

      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return null;
      }

      final position = await Geolocator.getLastKnownPosition();
      if (position != null) {
        return LatLng(position.latitude, position.longitude);
      }
    } catch (_) {
      // Gestion gracieuse des erreurs de capteurs
    }
    return null;
  }

  /// Sollicite les permissions de localisation et récupère les coordonnées GPS réelles de l'appareil
  /// avec un timeout court (3s) pour un démarrage fluide même en zone blanche.
  static Future<LatLng?> getCurrentPosition({
    bool promptPermission = true,
    int timeoutSeconds = 3,
  }) async {
    try {
      // 1. Vérification activation du capteur GPS
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return null;
      }

      // 2. Vérification et demande des permissions
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied && promptPermission) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          return null;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        return null;
      }

      // 3. Récupération de la position GPS précise (timeout court pour ne pas bloquer l'UI)
      Position? position;
      try {
        position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 3),
        );
      } catch (_) {
        // En cas de timeout ou signal faible, repli sur la dernière position connue
        position = await Geolocator.getLastKnownPosition();
      }

      position ??= await Geolocator.getLastKnownPosition();

      if (position != null) {
        return LatLng(position.latitude, position.longitude);
      }
    } catch (_) {
      // Gestion gracieuse des erreurs de capteurs
    }
    return null;
  }

  /// Calcule la distance orthodromique (Haversine) en kilomètres entre deux points GPS
  static double calculateHaversineKm(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const double earthRadiusKm = 6371.0;
    final dLat = _deg2rad(lat2 - lat1);
    final dLon = _deg2rad(lon2 - lon1);

    final a =
        math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(_deg2rad(lat1)) *
            math.cos(_deg2rad(lat2)) *
            math.sin(dLon / 2) *
            math.sin(dLon / 2);

    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    return earthRadiusKm * c;
  }

  /// Calcule le gisement/azimut (bearing) en degrés (0-360) du point 1 vers le point 2.
  /// 0° = Nord, 90° = Est, 180° = Sud, 270° = Ouest.
  static double calculateBearingDegrees(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    final lat1Rad = _deg2rad(lat1);
    final lat2Rad = _deg2rad(lat2);
    final dLonRad = _deg2rad(lon2 - lon1);

    final y = math.sin(dLonRad) * math.cos(lat2Rad);
    final x = math.cos(lat1Rad) * math.sin(lat2Rad) -
        math.sin(lat1Rad) * math.cos(lat2Rad) * math.cos(dLonRad);

    final bearingRad = math.atan2(y, x);
    final bearingDeg = _rad2deg(bearingRad);
    return (bearingDeg + 360) % 360;
  }

  static double _deg2rad(double deg) => deg * (math.pi / 180.0);

  static double _rad2deg(double rad) => rad * (180.0 / math.pi);
}
