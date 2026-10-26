import 'dart:math' as math;
import '../models/health_professional.dart';

/// Helper pur mathématique pour les calculs de distances géodésiques et tri hors-ligne
abstract final class GeoCalculator {
  /// Rayon moyen de la Terre en kilomètres (modèle sphérique WGS84)
  static const double earthRadiusKm = 6371.0;

  /// Calcule la distance orthodromique (en kilomètres) entre deux coordonnées GPS selon la formule de Haversine
  static double distanceBetween({
    required double startLatitude,
    required double startLongitude,
    required double endLatitude,
    required double endLongitude,
  }) {
    if (startLatitude == endLatitude && startLongitude == endLongitude) {
      return 0.0;
    }

    final dLat = _degreesToRadians(endLatitude - startLatitude);
    final dLon = _degreesToRadians(endLongitude - startLongitude);

    final lat1Rad = _degreesToRadians(startLatitude);
    final lat2Rad = _degreesToRadians(endLatitude);

    final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
        math.cos(lat1Rad) * math.cos(lat2Rad) * math.sin(dLon / 2) * math.sin(dLon / 2);

    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    final distance = earthRadiusKm * c;

    // Arrondi à deux décimales (précision ~10 mètres)
    return (distance * 100).roundToDouble() / 100;
  }

  /// Trie une liste d'établissements de santé par proximité croissante par rapport à la position de l'utilisateur
  static List<T> sortByProximity<T extends HealthProfessional>(
    List<T> items, {
    required double userLatitude,
    required double userLongitude,
  }) {
    final updatedList = items.map((item) {
      final dist = distanceBetween(
        startLatitude: userLatitude,
        startLongitude: userLongitude,
        endLatitude: item.latitude,
        endLongitude: item.longitude,
      );
      // Utilisation du copyWith du modèle pour conserver l'immuabilité
      return item.copyWith(distanceKm: dist) as T;
    }).toList();

    updatedList.sort((a, b) {
      final distA = a.distanceKm ?? double.infinity;
      final distB = b.distanceKm ?? double.infinity;
      return distA.compareTo(distB);
    });

    return List.unmodifiable(updatedList);
  }

  static double _degreesToRadians(double degrees) {
    return degrees * (math.pi / 180.0);
  }
}
