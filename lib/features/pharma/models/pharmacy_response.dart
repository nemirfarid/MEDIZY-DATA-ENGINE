enum AvailabilityStatus {
  available,
  equivalentAvailable,
  unavailable,
}

/// Réponse en 1 clic de l'officine pour le module Dispo-Médicaments.
class PharmacyResponse {
  final String responseId;
  final String requestId;
  final int pharmacyPlaceId;
  final String pharmacyName;
  final String pharmacyPhone;
  final String commune;
  final double distanceKm;
  final AvailabilityStatus status;
  final String? equivalentProposal;
  final DateTime? holdUntil;
  final DateTime createdAt;

  PharmacyResponse({
    required this.responseId,
    required this.requestId,
    required this.pharmacyPlaceId,
    required this.pharmacyName,
    required this.pharmacyPhone,
    required this.commune,
    required this.distanceKm,
    required this.status,
    this.equivalentProposal,
    this.holdUntil,
    required this.createdAt,
  });

  Map<String, dynamic> toJson() => {
    'responseId': responseId,
    'requestId': requestId,
    'pharmacyPlaceId': pharmacyPlaceId,
    'pharmacyName': pharmacyName,
    'pharmacyPhone': pharmacyPhone,
    'commune': commune,
    'distanceKm': distanceKm,
    'status': status.name,
    'equivalentProposal': equivalentProposal,
    'holdUntil': holdUntil?.toIso8601String(),
    'createdAt': createdAt.toIso8601String(),
  };

  factory PharmacyResponse.fromJson(Map<String, dynamic> json) => PharmacyResponse(
    responseId: json['responseId'] as String,
    requestId: json['requestId'] as String,
    pharmacyPlaceId: json['pharmacyPlaceId'] as int,
    pharmacyName: json['pharmacyName'] as String,
    pharmacyPhone: json['pharmacyPhone'] as String,
    commune: json['commune'] as String,
    distanceKm: (json['distanceKm'] as num).toDouble(),
    status: AvailabilityStatus.values.firstWhere(
      (e) => e.name == json['status'],
      orElse: () => AvailabilityStatus.unavailable,
    ),
    equivalentProposal: json['equivalentProposal'] as String?,
    holdUntil: json['holdUntil'] != null ? DateTime.parse(json['holdUntil'] as String) : null,
    createdAt: DateTime.parse(json['createdAt'] as String),
  );
}
