import 'dart:convert';
import 'package:crypto/crypto.dart';

enum MedicationRequestStatus {
  active,
  reserved,
  fulfilled,
  expired,
  cancelled,
}

/// Demande géolocalisée de recherche de médicament pour le module "Dispo-Médicaments".
/// Conforme à la Loi 18-07 : l'identité du patient est strictement masquée via un jeton d'anonymat.
class MedicationRequest {
  final String requestId;
  final String dci; // Dénomination Commune Internationale (ex: Amoxicilline)
  final String? brandName; // Nom commercial recherché (ex: Augmentin)
  final String dosage; // Ex: 1g, 500mg
  final String form; // Ex: Comprimé, Sirop, Injectable
  final double latitude;
  final double longitude;
  final double radiusKm; // Rayon de recherche (5.0 à 15.0 km)
  final String patientAnonymityToken;
  final DateTime createdAt;
  final DateTime expiresAt;
  MedicationRequestStatus status;
  int? reservedPharmacyPlaceId;

  MedicationRequest({
    required this.requestId,
    required this.dci,
    this.brandName,
    required this.dosage,
    required this.form,
    required this.latitude,
    required this.longitude,
    this.radiusKm = 10.0,
    required this.patientAnonymityToken,
    required this.createdAt,
    required this.expiresAt,
    this.status = MedicationRequestStatus.active,
    this.reservedPharmacyPlaceId,
  });

  /// Création d'un token d'anonymat cryptographique sans trace d'IP ni d'identité directe
  static String generateAnonymityToken(String patientSecret) {
    final now = DateTime.now().microsecondsSinceEpoch.toString();
    final bytes = utf8.encode('$patientSecret:$now:DZ_MEDIZY_ANON');
    return 'ANON-${sha256.convert(bytes).toString().substring(0, 12).toUpperCase()}';
  }

  bool get isExpired => DateTime.now().isAfter(expiresAt);

  Map<String, dynamic> toJson() => {
    'requestId': requestId,
    'dci': dci,
    'brandName': brandName,
    'dosage': dosage,
    'form': form,
    'latitude': latitude,
    'longitude': longitude,
    'radiusKm': radiusKm,
    'patientAnonymityToken': patientAnonymityToken,
    'createdAt': createdAt.toIso8601String(),
    'expiresAt': expiresAt.toIso8601String(),
    'status': status.name,
    'reservedPharmacyPlaceId': reservedPharmacyPlaceId,
  };

  factory MedicationRequest.fromJson(Map<String, dynamic> json) => MedicationRequest(
    requestId: json['requestId'] as String,
    dci: json['dci'] as String,
    brandName: json['brandName'] as String?,
    dosage: json['dosage'] as String,
    form: json['form'] as String,
    latitude: (json['latitude'] as num).toDouble(),
    longitude: (json['longitude'] as num).toDouble(),
    radiusKm: (json['radiusKm'] as num?)?.toDouble() ?? 10.0,
    patientAnonymityToken: json['patientAnonymityToken'] as String,
    createdAt: DateTime.parse(json['createdAt'] as String),
    expiresAt: DateTime.parse(json['expiresAt'] as String),
    status: MedicationRequestStatus.values.firstWhere(
      (e) => e.name == json['status'],
      orElse: () => MedicationRequestStatus.active,
    ),
    reservedPharmacyPlaceId: json['reservedPharmacyPlaceId'] as int?,
  );
}
