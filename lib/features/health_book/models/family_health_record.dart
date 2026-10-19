/// Statut d'administration d'un vaccin du calendrier national algérien.
enum VaccineStatus {
  completed,
  scheduled,
  delayed,
}

class VaccineRecord {
  final String vaccineName;
  final String targetAge;
  final String diseasesPrevented;
  final DateTime scheduledDate;
  DateTime? administeredDate;
  VaccineStatus status;
  String? batchNumber;
  String? administeringCenter;

  VaccineRecord({
    required this.vaccineName,
    required this.targetAge,
    required this.diseasesPrevented,
    required this.scheduledDate,
    this.administeredDate,
    this.status = VaccineStatus.scheduled,
    this.batchNumber,
    this.administeringCenter,
  });

  Map<String, dynamic> toJson() => {
    'vaccineName': vaccineName,
    'targetAge': targetAge,
    'diseasesPrevented': diseasesPrevented,
    'scheduledDate': scheduledDate.toIso8601String(),
    'administeredDate': administeredDate?.toIso8601String(),
    'status': status.name,
    'batchNumber': batchNumber,
    'administeringCenter': administeringCenter,
  };

  factory VaccineRecord.fromJson(Map<String, dynamic> json) => VaccineRecord(
    vaccineName: json['vaccineName'] as String,
    targetAge: json['targetAge'] as String,
    diseasesPrevented: json['diseasesPrevented'] as String,
    scheduledDate: DateTime.parse(json['scheduledDate'] as String),
    administeredDate: json['administeredDate'] != null ? DateTime.parse(json['administeredDate'] as String) : null,
    status: VaccineStatus.values.firstWhere(
      (e) => e.name == json['status'],
      orElse: () => VaccineStatus.scheduled,
    ),
    batchNumber: json['batchNumber'] as String?,
    administeringCenter: json['administeringCenter'] as String?,
  );
}

/// Mesure de glycémie capillaire pour le suivi du diabète.
class GlycemiaEntry {
  final double valueMgDl;
  final String context; // 'a_jeun', 'post_prandial', 'coucher'
  final DateTime recordedAt;

  GlycemiaEntry({
    required this.valueMgDl,
    required this.context,
    required this.recordedAt,
  });

  bool get isNormal {
    if (context == 'a_jeun') return valueMgDl >= 70.0 && valueMgDl <= 126.0;
    return valueMgDl < 180.0;
  }

  Map<String, dynamic> toJson() => {
    'valueMgDl': valueMgDl,
    'context': context,
    'recordedAt': recordedAt.toIso8601String(),
  };

  factory GlycemiaEntry.fromJson(Map<String, dynamic> json) => GlycemiaEntry(
    valueMgDl: (json['valueMgDl'] as num).toDouble(),
    context: json['context'] as String,
    recordedAt: DateTime.parse(json['recordedAt'] as String),
  );
}

/// Mesure tensionnelle pour le suivi de l'HTA.
class BloodPressureEntry {
  final int systolic; // Ex: 120
  final int diastolic; // Ex: 80
  final int pulse; // Ex: 72
  final DateTime recordedAt;

  BloodPressureEntry({
    required this.systolic,
    required this.diastolic,
    required this.pulse,
    required this.recordedAt,
  });

  bool get isHypertensive => systolic >= 140 || diastolic >= 90;

  Map<String, dynamic> toJson() => {
    'systolic': systolic,
    'diastolic': diastolic,
    'pulse': pulse,
    'recordedAt': recordedAt.toIso8601String(),
  };

  factory BloodPressureEntry.fromJson(Map<String, dynamic> json) => BloodPressureEntry(
    systolic: json['systolic'] as int,
    diastolic: json['diastolic'] as int,
    pulse: json['pulse'] as int,
    recordedAt: DateTime.parse(json['recordedAt'] as String),
  );
}

/// Carnet de santé familial numérique sécurisé en local (AES-256).
class FamilyHealthRecord {
  final String recordId;
  final String personName;
  final DateTime birthDate;
  final String bloodGroup; // 'A+', 'O+', 'B-', etc.
  final List<VaccineRecord> vaccines;
  final List<GlycemiaEntry> glycemiaLogs;
  final List<BloodPressureEntry> bloodPressureLogs;

  FamilyHealthRecord({
    required this.recordId,
    required this.personName,
    required this.birthDate,
    required this.bloodGroup,
    List<VaccineRecord>? vaccines,
    List<GlycemiaEntry>? glycemiaLogs,
    List<BloodPressureEntry>? bloodPressureLogs,
  })  : vaccines = vaccines ?? [],
        glycemiaLogs = glycemiaLogs ?? [],
        bloodPressureLogs = bloodPressureLogs ?? [];

  /// Initialise automatiquement le calendrier vaccinal national officiel algérien pour un nouveau-né
  static FamilyHealthRecord createNewbornRecord({
    required String recordId,
    required String childName,
    required DateTime birthDate,
    required String bloodGroup,
  }) {
    final record = FamilyHealthRecord(
      recordId: recordId,
      personName: childName,
      birthDate: birthDate,
      bloodGroup: bloodGroup,
    );

    // Calendrier officiel du Ministère de la Santé (MSPRH)
    record.vaccines.addAll([
      VaccineRecord(
        vaccineName: 'BCG + VPO 0 + Hépatite B 1',
        targetAge: 'Naissance (Jour 0)',
        diseasesPrevented: 'Tuberculose, Poliomyélite, Hépatite B',
        scheduledDate: birthDate,
      ),
      VaccineRecord(
        vaccineName: 'DTCa-VPI-Hib-HepB (1ère dose) + Pneumocoque 1',
        targetAge: '2 mois',
        diseasesPrevented: 'Diphtérie, Tétanos, Coqueluche, Polio, Hib, Hépatite B, Infections à pneumocoque',
        scheduledDate: birthDate.add(const Duration(days: 60)),
      ),
      VaccineRecord(
        vaccineName: 'DTCa-VPI-Hib-HepB (2ème dose) + Pneumocoque 2',
        targetAge: '4 mois',
        diseasesPrevented: 'Diphtérie, Tétanos, Coqueluche, Polio, Hib, Hépatite B, Pneumocoque',
        scheduledDate: birthDate.add(const Duration(days: 120)),
      ),
      VaccineRecord(
        vaccineName: 'DTCa-VPI-Hib-HepB (Rappel) + ROR 1 + Pneumocoque (Rappel)',
        targetAge: '11 mois',
        diseasesPrevented: 'Rappel Hexavalent, Rougeole, Oreillons, Rubéole, Pneumocoque',
        scheduledDate: birthDate.add(const Duration(days: 335)),
      ),
      VaccineRecord(
        vaccineName: 'ROR (2ème dose)',
        targetAge: '18 mois',
        diseasesPrevented: 'Rougeole, Oreillons, Rubéole',
        scheduledDate: birthDate.add(const Duration(days: 545)),
      ),
      VaccineRecord(
        vaccineName: 'DTC-VPO (Rappel)',
        targetAge: '6 ans',
        diseasesPrevented: 'Diphtérie, Tétanos, Coqueluche, Poliomyélite',
        scheduledDate: birthDate.add(const Duration(days: 2190)),
      ),
    ]);

    return record;
  }
}
