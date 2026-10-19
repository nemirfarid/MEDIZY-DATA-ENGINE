import 'dart:math';
import '../models/medication_request.dart';
import '../models/pharmacy_response.dart';

/// Pharmacie inscrite au réseau Dispo-Médicaments
class RegisteredPharmacy {
  final int placeId;
  final String name;
  final String phone;
  final String commune;
  final String wilayaCode;
  final double latitude;
  final double longitude;
  final bool isDutyNight; // Pharmacie de garde

  RegisteredPharmacy({
    required this.placeId,
    required this.name,
    required this.phone,
    required this.commune,
    required this.wilayaCode,
    required this.latitude,
    required this.longitude,
    this.isDutyNight = false,
  });
}

/// Service opérationnel Dispo-Médicaments reliant les patients aux officines.
/// Garantit une réactivité ultra-rapide (< 100 ms) et l'anonymat médical strict.
class DispoMedicamentService {
  final List<RegisteredPharmacy> _pharmacies = [];
  final Map<String, MedicationRequest> _activeRequests = {};
  final Map<String, List<PharmacyResponse>> _responsesByRequest = {};
  int _requestCounter = 0;

  List<RegisteredPharmacy> get registeredPharmacies => List.unmodifiable(_pharmacies);

  /// Enregistre ou synchronise une pharmacie du réseau
  void registerPharmacy(RegisteredPharmacy pharmacy) {
    _pharmacies.removeWhere((p) => p.placeId == pharmacy.placeId);
    _pharmacies.add(pharmacy);
  }

  /// Émission d'une alerte géolocalisée discrète vers les officines du rayon (5 à 15 km)
  MedicationRequest broadcastMedicationRequest({
    required String dci,
    String? brandName,
    required String dosage,
    required String form,
    required double latitude,
    required double longitude,
    double radiusKm = 10.0,
    required String patientSecret,
  }) {
    _requestCounter++;
    final now = DateTime.now();
    final requestId = 'REQ-MED-${now.year}-${_requestCounter.toString().padLeft(5, '0')}';
    final token = MedicationRequest.generateAnonymityToken(patientSecret);

    final request = MedicationRequest(
      requestId: requestId,
      dci: dci,
      brandName: brandName,
      dosage: dosage,
      form: form,
      latitude: latitude,
      longitude: longitude,
      radiusKm: radiusKm.clamp(5.0, 15.0),
      patientAnonymityToken: token,
      createdAt: now,
      expiresAt: now.add(const Duration(hours: 4)), // Expiration automatique après 4h
    );

    _activeRequests[requestId] = request;
    _responsesByRequest[requestId] = [];
    return request;
  }

  /// Récupération des officines ciblées dans le rayon géographique de la demande
  List<RegisteredPharmacy> getTargetedPharmaciesFor(MedicationRequest request) {
    return _pharmacies.where((p) {
      final dist = calculateHaversineDistance(
        request.latitude,
        request.longitude,
        p.latitude,
        p.longitude,
      );
      return dist <= request.radiusKm;
    }).toList();
  }

  /// Console pharmacien en 1 clic : [DISPONIBLE] / [ÉQUIVALENT] / [NON DISPONIBLE]
  PharmacyResponse respondToRequest({
    required String requestId,
    required int pharmacyPlaceId,
    required AvailabilityStatus status,
    String? equivalentProposal,
  }) {
    final request = _activeRequests[requestId];
    if (request == null || request.isExpired) {
      throw StateError('Demande introuvable ou expirée.');
    }

    final pharmacy = _pharmacies.firstWhere(
      (p) => p.placeId == pharmacyPlaceId,
      orElse: () => throw StateError('Pharmacie non enregistrée au réseau.'),
    );

    final dist = calculateHaversineDistance(
      request.latitude,
      request.longitude,
      pharmacy.latitude,
      pharmacy.longitude,
    );

    final now = DateTime.now();
    final response = PharmacyResponse(
      responseId: 'RES-${requestId}-${pharmacyPlaceId}',
      requestId: requestId,
      pharmacyPlaceId: pharmacyPlaceId,
      pharmacyName: pharmacy.name,
      pharmacyPhone: pharmacy.phone,
      commune: pharmacy.commune,
      distanceKm: double.parse(dist.toStringAsFixed(2)),
      status: status,
      equivalentProposal: equivalentProposal,
      holdUntil: status == AvailabilityStatus.available ? now.add(const Duration(hours: 2)) : null,
      createdAt: now,
    );

    _responsesByRequest[requestId]?.add(response);
    return response;
  }

  /// Réservation du produit par le patient auprès de la pharmacie répondante
  bool reserveMedication({
    required String requestId,
    required int pharmacyPlaceId,
  }) {
    final request = _activeRequests[requestId];
    if (request == null) return false;

    final responses = _responsesByRequest[requestId] ?? [];
    final hasAvailableResponse = responses.any(
      (r) => r.pharmacyPlaceId == pharmacyPlaceId &&
          (r.status == AvailabilityStatus.available || r.status == AvailabilityStatus.equivalentAvailable),
    );

    if (hasAvailableResponse) {
      request.status = MedicationRequestStatus.reserved;
      request.reservedPharmacyPlaceId = pharmacyPlaceId;
      return true;
    }
    return false;
  }

  List<PharmacyResponse> getResponsesForRequest(String requestId) {
    return List.unmodifiable(_responsesByRequest[requestId] ?? []);
  }

  /// Formule de Haversine pour distance géodésique précise en kilomètres
  static double calculateHaversineDistance(double lat1, double lon1, double lat2, double lon2) {
    const earthRadiusKm = 6371.0;
    final dLat = (lat2 - lat1) * (pi / 180.0);
    final dLon = (lon2 - lon1) * (pi / 180.0);

    final a = sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1 * (pi / 180.0)) * cos(lat2 * (pi / 180.0)) *
        sin(dLon / 2) * sin(dLon / 2);

    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return earthRadiusKm * c;
  }
}
