import 'dart:convert';
import 'package:crypto/crypto.dart';

enum TicketStatus {
  waiting,
  called,
  inConsultation,
  completed,
  cancelled,
  noShow,
}

enum AppointmentType {
  walkIn,
  scheduled,
}

/// Billet de consultation virtuel pour cabinet médical / clinique Santé DZ Medizy.
class MedicalTicket {
  final String ticketId;
  final int ticketNumber;
  final int placeId;
  final String patientAlias;
  final String patientPhoneHash;
  final bool isUrgent;
  final AppointmentType appointmentType;
  final DateTime createdAt;
  TicketStatus status;
  DateTime? calledAt;
  DateTime? inConsultationAt;
  DateTime? completedAt;
  DateTime? estimatedConsultationTime;

  MedicalTicket({
    required this.ticketId,
    required this.ticketNumber,
    required this.placeId,
    required this.patientAlias,
    required this.patientPhoneHash,
    this.isUrgent = false,
    this.appointmentType = AppointmentType.walkIn,
    required this.createdAt,
    this.status = TicketStatus.waiting,
    this.calledAt,
    this.inConsultationAt,
    this.completedAt,
    this.estimatedConsultationTime,
  });

  /// Hachage cryptographique du téléphone pour anonymat conforme à la Loi 18-07
  static String hashPhone(String? phone) {
    if (phone == null || phone.isEmpty) return 'ANON_PATIENT';
    final bytes = utf8.encode(phone.trim().replaceAll(RegExp(r'\s+'), ''));
    return sha256.convert(bytes).toString().substring(0, 16);
  }

  Map<String, dynamic> toJson() => {
    'ticketId': ticketId,
    'ticketNumber': ticketNumber,
    'placeId': placeId,
    'patientAlias': patientAlias,
    'patientPhoneHash': patientPhoneHash,
    'isUrgent': isUrgent,
    'appointmentType': appointmentType.name,
    'createdAt': createdAt.toIso8601String(),
    'status': status.name,
    'calledAt': calledAt?.toIso8601String(),
    'inConsultationAt': inConsultationAt?.toIso8601String(),
    'completedAt': completedAt?.toIso8601String(),
    'estimatedConsultationTime': estimatedConsultationTime?.toIso8601String(),
  };

  factory MedicalTicket.fromJson(Map<String, dynamic> json) => MedicalTicket(
    ticketId: json['ticketId'] as String,
    ticketNumber: json['ticketNumber'] as int,
    placeId: json['placeId'] as int,
    patientAlias: json['patientAlias'] as String,
    patientPhoneHash: json['patientPhoneHash'] as String,
    isUrgent: json['isUrgent'] as bool? ?? false,
    appointmentType: AppointmentType.values.firstWhere(
      (e) => e.name == json['appointmentType'],
      orElse: () => AppointmentType.walkIn,
    ),
    createdAt: DateTime.parse(json['createdAt'] as String),
    status: TicketStatus.values.firstWhere(
      (e) => e.name == json['status'],
      orElse: () => TicketStatus.waiting,
    ),
    calledAt: json['calledAt'] != null ? DateTime.parse(json['calledAt'] as String) : null,
    inConsultationAt: json['inConsultationAt'] != null ? DateTime.parse(json['inConsultationAt'] as String) : null,
    completedAt: json['completedAt'] != null ? DateTime.parse(json['completedAt'] as String) : null,
    estimatedConsultationTime: json['estimatedConsultationTime'] != null
        ? DateTime.parse(json['estimatedConsultationTime'] as String)
        : null,
  );
}
