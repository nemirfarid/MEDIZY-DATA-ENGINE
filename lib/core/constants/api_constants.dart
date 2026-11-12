/// Configuration des points d'accès API pour la synchronisation et les services connectés MEDIZY
class ApiConstants {
  /// Adresse IP locale du poste de développement (Réseau Wi-Fi)
  static const String localWifiHost = '10.188.170.227';

  /// Adresse de bouclage de l'émulateur Android
  static const String emulatorHost = '10.0.2.2';

  /// Port d'écoute du serveur backend FastAPI
  static const int apiPort = 8000;

  /// URL de base courante pour le ciblage du backend MEDIZY v1.0.0-prod
  /// En test sur smartphone physique connecté au même Wi-Fi : http://10.188.170.227:8000
  static const String baseUrl = 'http://$localWifiHost:$apiPort';

  // --- Points d'accès de l'API REST v1 ---
  static const String healthUrl = '$baseUrl/health';
  static const String nearbyUrl = '$baseUrl/api/v1/facilities/nearby';
  static const String searchUrl = '$baseUrl/api/v1/facilities/search';
  static const String suggestUrl = '$baseUrl/api/v1/facilities/suggest';
  static const String exportLatestUrl = '$baseUrl/api/v1/facilities/export/latest';

  /// Timeout par défaut pour les requêtes réseau (en secondes)
  static const int requestTimeoutSeconds = 10;
}
