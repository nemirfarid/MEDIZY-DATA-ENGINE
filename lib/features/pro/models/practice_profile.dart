enum ClaimVerificationStatus {
  unclaimed,
  pendingValidation,
  verified,
  rejected,
}

/// Profil professionnel Medizy Pro pour médecin, dentiste ou clinique.
class PracticeProfile {
  final int placeId;
  final String establishmentName;
  final String specialty;
  final String wilayaCode;
  final String commune;
  final String officialPhone;
  bool isClaimed;
  ClaimVerificationStatus verificationStatus;
  String? practitionerName;
  String? nationalIdOrOrderNumber;
  String? verificationCode;
  String subscriptionPlan;
  bool isTrialActive;
  DateTime? trialEndsAt;
  DateTime? subscriptionEndsAt;
  int consultationDurationMinutes;
  int maxDailySlots;

  PracticeProfile({
    required this.placeId,
    required this.establishmentName,
    required this.specialty,
    required this.wilayaCode,
    required this.commune,
    required this.officialPhone,
    this.isClaimed = false,
    this.verificationStatus = ClaimVerificationStatus.unclaimed,
    this.practitionerName,
    this.nationalIdOrOrderNumber,
    this.verificationCode,
    this.subscriptionPlan = 'medizy_pro_monthly',
    this.isTrialActive = false,
    this.trialEndsAt,
    this.subscriptionEndsAt,
    this.consultationDurationMinutes = 15,
    this.maxDailySlots = 35,
  });

  bool get hasActiveAccess => isTrialActive || (subscriptionEndsAt != null && subscriptionEndsAt!.isAfter(DateTime.now()));

  Map<String, dynamic> toJson() => {
    'placeId': placeId,
    'establishmentName': establishmentName,
    'specialty': specialty,
    'wilayaCode': wilayaCode,
    'commune': commune,
    'officialPhone': officialPhone,
    'isClaimed': isClaimed,
    'verificationStatus': verificationStatus.name,
    'practitionerName': practitionerName,
    'nationalIdOrOrderNumber': nationalIdOrOrderNumber,
    'verificationCode': verificationCode,
    'subscriptionPlan': subscriptionPlan,
    'isTrialActive': isTrialActive,
    'trialEndsAt': trialEndsAt?.toIso8601String(),
    'subscriptionEndsAt': subscriptionEndsAt?.toIso8601String(),
    'consultationDurationMinutes': consultationDurationMinutes,
    'maxDailySlots': maxDailySlots,
  };

  factory PracticeProfile.fromJson(Map<String, dynamic> json) => PracticeProfile(
    placeId: json['placeId'] as int,
    establishmentName: json['establishmentName'] as String,
    specialty: json['specialty'] as String,
    wilayaCode: json['wilayaCode'] as String,
    commune: json['commune'] as String,
    officialPhone: json['officialPhone'] as String,
    isClaimed: json['isClaimed'] as bool? ?? false,
    verificationStatus: ClaimVerificationStatus.values.firstWhere(
      (e) => e.name == json['verificationStatus'],
      orElse: () => ClaimVerificationStatus.unclaimed,
    ),
    practitionerName: json['practitionerName'] as String?,
    nationalIdOrOrderNumber: json['nationalIdOrOrderNumber'] as String?,
    verificationCode: json['verificationCode'] as String?,
    subscriptionPlan: json['subscriptionPlan'] as String? ?? 'medizy_pro_monthly',
    isTrialActive: json['isTrialActive'] as bool? ?? false,
    trialEndsAt: json['trialEndsAt'] != null ? DateTime.parse(json['trialEndsAt'] as String) : null,
    subscriptionEndsAt: json['subscriptionEndsAt'] != null ? DateTime.parse(json['subscriptionEndsAt'] as String) : null,
    consultationDurationMinutes: json['consultationDurationMinutes'] as int? ?? 15,
    maxDailySlots: json['maxDailySlots'] as int? ?? 35,
  );
}
