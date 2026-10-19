enum PaymentMethod {
  cib,
  edahabia,
  baridimob,
  virementCcp,
}

enum InvoiceStatus {
  paid,
  pending,
  failed,
  refunded,
}

/// Facture et quittance dématérialisée conforme aux normes fiscales algériennes.
class Invoice {
  final String invoiceNumber; // Ex: FAC-2026-10-0089
  final int placeId;
  final String practitionerOrEntityName;
  final String? nif; // Numéro d'Identification Fiscale
  final String? nis; // Numéro d'Identification Statistique
  final String? rc;  // Registre de Commerce / N° Agrément MSPRH
  final String planId;
  final String planTitle;
  final double amountDzd;
  final double vatRate; // TVA 0% (prestations médicales) ou 19%
  final PaymentMethod paymentMethod;
  final String transactionId;
  final String? satimApprovalCode;
  final InvoiceStatus status;
  final DateTime issuedAt;
  final DateTime periodStart;
  final DateTime periodEnd;

  Invoice({
    required this.invoiceNumber,
    required this.placeId,
    required this.practitionerOrEntityName,
    this.nif,
    this.nis,
    this.rc,
    required this.planId,
    required this.planTitle,
    required this.amountDzd,
    this.vatRate = 0.0,
    required this.paymentMethod,
    required this.transactionId,
    this.satimApprovalCode,
    this.status = InvoiceStatus.paid,
    required this.issuedAt,
    required this.periodStart,
    required this.periodEnd,
  });

  double get totalWithVat => amountDzd * (1.0 + vatRate);

  String get formattedAmountDzd => '${amountDzd.toStringAsFixed(2)} DZD';

  Map<String, dynamic> toJson() => {
    'invoiceNumber': invoiceNumber,
    'placeId': placeId,
    'practitionerOrEntityName': practitionerOrEntityName,
    'nif': nif,
    'nis': nis,
    'rc': rc,
    'planId': planId,
    'planTitle': planTitle,
    'amountDzd': amountDzd,
    'vatRate': vatRate,
    'paymentMethod': paymentMethod.name,
    'transactionId': transactionId,
    'satimApprovalCode': satimApprovalCode,
    'status': status.name,
    'issuedAt': issuedAt.toIso8601String(),
    'periodStart': periodStart.toIso8601String(),
    'periodEnd': periodEnd.toIso8601String(),
  };

  factory Invoice.fromJson(Map<String, dynamic> json) => Invoice(
    invoiceNumber: json['invoiceNumber'] as String,
    placeId: json['placeId'] as int,
    practitionerOrEntityName: json['practitionerOrEntityName'] as String,
    nif: json['nif'] as String?,
    nis: json['nis'] as String?,
    rc: json['rc'] as String?,
    planId: json['planId'] as String,
    planTitle: json['planTitle'] as String,
    amountDzd: (json['amountDzd'] as num).toDouble(),
    vatRate: (json['vatRate'] as num?)?.toDouble() ?? 0.0,
    paymentMethod: PaymentMethod.values.firstWhere(
      (e) => e.name == json['paymentMethod'],
      orElse: () => PaymentMethod.edahabia,
    ),
    transactionId: json['transactionId'] as String,
    satimApprovalCode: json['satimApprovalCode'] as String?,
    status: InvoiceStatus.values.firstWhere(
      (e) => e.name == json['status'],
      orElse: () => InvoiceStatus.paid,
    ),
    issuedAt: DateTime.parse(json['issuedAt'] as String),
    periodStart: DateTime.parse(json['periodStart'] as String),
    periodEnd: DateTime.parse(json['periodEnd'] as String),
  );
}
