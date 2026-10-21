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

  /// Sollicite les permissions de localisation et récupère les coordonnées GPS réelles de l'appareil
  static Future<LatLng?> getCurrentLocation({bool promptPermission = true}) async {
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

      // 3. Récupération de la position GPS précise (haute précision, timeout 5s)
      Position? position;
      try {
        position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 5),
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
}
