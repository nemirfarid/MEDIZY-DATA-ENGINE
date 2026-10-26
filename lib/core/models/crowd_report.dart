import 'package:meta/meta.dart';

/// Typologie des anomalies sanitaires pouvant être signalées par les usagers
enum ReportType {
  closedPermanently('Établissement fermé définitivement'),
  wrongPhoneNumber('Numéro de téléphone erroné ou non attribué'),
  wrongAddress('Adresse ou position GPS incorrecte'),
  modifiedHours('Horaires d\'ouverture modifiés'),
  chifaNotAccepted('Conventionnement Chifa non actif'),
  other('Autre anomalie');

  final String label;
  const ReportType(this.label);

  static ReportType fromString(String? value) {
    for (final type in ReportType.values) {
      if (type.name == value || type.label == value) {
        return type;
      }
    }
    return ReportType.other;
  }
}

/// Modèle immuable d'un signalement d'anomalie en file d'attente locale hors-ligne
@immutable
class CrowdReport {
  final int? id;
  final int facilityId;
  final String facilityName;
  final ReportType reportType;
  final String? description;
  final String? suggestedPhone;
  final String? suggestedAddress;
  final DateTime createdAt;
  final int retryCount;
  final DateTime? syncedAt;
  final bool isSynced;

  const CrowdReport({
    this.id,
    required this.facilityId,
    required this.facilityName,
    required this.reportType,
    this.description,
    this.suggestedPhone,
    this.suggestedAddress,
    required this.createdAt,
    this.retryCount = 0,
    this.syncedAt,
    this.isSynced = false,
  });

  factory CrowdReport.fromRow(Map<String, Object?> row) {
    return CrowdReport(
      id: row['id'] != null ? (row['id'] as num).toInt() : null,
      facilityId: (row['facility_id'] as num).toInt(),
      facilityName: (row['facility_name'] as String?) ?? '',
      reportType: ReportType.fromString(row['report_type'] as String?),
      description: row['description'] as String?,
      suggestedPhone: row['suggested_phone'] as String?,
      suggestedAddress: row['suggested_address'] as String?,
      createdAt: DateTime.tryParse(row['created_at']?.toString() ?? '') ?? DateTime.now().toUtc(),
      retryCount: (row['retry_count'] as num?)?.toInt() ?? 0,
      syncedAt: row['synced_at'] != null ? DateTime.tryParse(row['synced_at'].toString()) : null,
      isSynced: (row['is_synced'] as num?)?.toInt() == 1,
    );
  }

  Map<String, Object?> toMap() {
    return {
      if (id != null) 'id': id,
      'facility_id': facilityId,
      'facility_name': facilityName,
      'report_type': reportType.name,
      'description': description,
      'suggested_phone': suggestedPhone,
      'suggested_address': suggestedAddress,
      'created_at': createdAt.toIso8601String(),
      'retry_count': retryCount,
      if (syncedAt != null) 'synced_at': syncedAt!.toIso8601String(),
      'is_synced': isSynced ? 1 : 0,
    };
  }

  CrowdReport copyWith({
    int? id,
    int? facilityId,
    String? facilityName,
    ReportType? reportType,
    String? description,
    String? suggestedPhone,
    String? suggestedAddress,
    DateTime? createdAt,
    int? retryCount,
    DateTime? syncedAt,
    bool? isSynced,
  }) {
    return CrowdReport(
      id: id ?? this.id,
      facilityId: facilityId ?? this.facilityId,
      facilityName: facilityName ?? this.facilityName,
      reportType: reportType ?? this.reportType,
      description: description ?? this.description,
      suggestedPhone: suggestedPhone ?? this.suggestedPhone,
      suggestedAddress: suggestedAddress ?? this.suggestedAddress,
      createdAt: createdAt ?? this.createdAt,
      retryCount: retryCount ?? this.retryCount,
      syncedAt: syncedAt ?? this.syncedAt,
      isSynced: isSynced ?? this.isSynced,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CrowdReport &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          facilityId == other.facilityId &&
          reportType == other.reportType &&
          createdAt == other.createdAt;

  @override
  int get hashCode => id.hashCode ^ facilityId.hashCode ^ reportType.hashCode ^ createdAt.hashCode;

  @override
  String toString() =>
      'CrowdReport(id: $id, facilityId: $facilityId, type: ${reportType.name}, synced: $isSynced)';
}
