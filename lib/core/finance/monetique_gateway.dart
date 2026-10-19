import 'models/subscription_plan.dart';
import 'models/invoice.dart';
import 'satim_simulator.dart';

class PaymentCheckoutResult {
  final bool isSuccess;
  final String? orderId;
  final String? approvalCode;
  final Invoice? invoice;
  final String? errorMessage;
  final bool requiresOtp;

  PaymentCheckoutResult({
    required this.isSuccess,
    this.orderId,
    this.approvalCode,
    this.invoice,
    this.errorMessage,
    this.requiresOtp = false,
  });
}

/// Passerelle souveraine de paiement électronique et monétique Santé DZ Medizy.
/// Prend en charge les cartes CIB, EDAHABIA (Algérie Poste) et les virements BaridiMob.
class MonetiqueGateway {
  final SatimSimulator _satimSimulator;
  final Map<int, List<Invoice>> _invoicesByPlace = {};
  int _invoiceCounter = 0;

  MonetiqueGateway({SatimSimulator? satimSimulator})
      : _satimSimulator = satimSimulator ?? SatimSimulator();

  SatimSimulator get satimSimulator => _satimSimulator;

  List<Invoice> getInvoicesForPlace(int placeId) =>
      List.unmodifiable(_invoicesByPlace[placeId] ?? []);

  /// Étape 1 : Initier le paiement d'un abonnement via carte CIB ou EDAHABIA
  PaymentCheckoutResult initiateCardCheckout({
    required int placeId,
    required String entityName,
    required String planId,
    required String pan,
    required String expiryDate,
    required String cvv,
  }) {
    final plan = SubscriptionPlan.findById(planId);

    final auth = _satimSimulator.requestPaymentAuthorization(
      pan: pan,
      expiryDate: expiryDate,
      cvv: cvv,
      amountDzd: plan.amountDzd,
    );

    if (!auth.isSuccess) {
      return PaymentCheckoutResult(
        isSuccess: false,
        errorMessage: auth.errorMessage,
      );
    }

    return PaymentCheckoutResult(
      isSuccess: true,
      orderId: auth.orderId,
      requiresOtp: true,
    );
  }

  /// Étape 2 : Confirmer l'OTP 3-D Secure SATIM et générer la facture fiscale
  PaymentCheckoutResult confirmCardCheckout({
    required int placeId,
    required String entityName,
    required String planId,
    required String orderId,
    required String otp,
    PaymentMethod paymentMethod = PaymentMethod.edahabia,
  }) {
    final plan = SubscriptionPlan.findById(planId);

    final confirmation = _satimSimulator.confirmPaymentWithOtp(
      orderId: orderId,
      enteredOtp: otp,
    );

    if (!confirmation.isSuccess) {
      return PaymentCheckoutResult(
        isSuccess: false,
        errorMessage: confirmation.errorMessage,
      );
    }

    _invoiceCounter++;
    final now = DateTime.now();
    final invoiceNumber = 'FAC-${now.year}-${now.month.toString().padLeft(2, '0')}-${_invoiceCounter.toString().padLeft(5, '0')}';

    final invoice = Invoice(
      invoiceNumber: invoiceNumber,
      placeId: placeId,
      practitionerOrEntityName: entityName,
      nif: '001616098234123',
      nis: '098234120938',
      rc: '16/00-849120B26',
      planId: plan.id,
      planTitle: plan.title,
      amountDzd: plan.amountDzd,
      vatRate: 0.0, // Prestation de santé exonérée de TVA
      paymentMethod: paymentMethod,
      transactionId: orderId,
      satimApprovalCode: confirmation.approvalCode,
      status: InvoiceStatus.paid,
      issuedAt: now,
      periodStart: now,
      periodEnd: now.add(Duration(days: plan.billingPeriodDays)),
    );

    _invoicesByPlace.putIfAbsent(placeId, () => []).add(invoice);

    return PaymentCheckoutResult(
      isSuccess: true,
      orderId: orderId,
      approvalCode: confirmation.approvalCode,
      invoice: invoice,
    );
  }

  /// Règlement alternatif par virement instantané BaridiMob avec référence RIP
  PaymentCheckoutResult processBaridiMobCheckout({
    required int placeId,
    required String entityName,
    required String planId,
    required String rip, // 20 chiffres
    required String transactionReference,
  }) {
    final cleanRip = rip.replaceAll(RegExp(r'\D'), '');
    if (!validateAlgerianRip(cleanRip)) {
      return PaymentCheckoutResult(
        isSuccess: false,
        errorMessage: 'Numéro RIP BaridiMob invalide (format 20 chiffres requis).',
      );
    }

    if (transactionReference.trim().isEmpty) {
      return PaymentCheckoutResult(
        isSuccess: false,
        errorMessage: 'La référence de transaction BaridiMob est obligatoire.',
      );
    }

    final plan = SubscriptionPlan.findById(planId);
    _invoiceCounter++;
    final now = DateTime.now();
    final invoiceNumber = 'FAC-BMOB-${now.year}-${_invoiceCounter.toString().padLeft(5, '0')}';

    final invoice = Invoice(
      invoiceNumber: invoiceNumber,
      placeId: placeId,
      practitionerOrEntityName: entityName,
      planId: plan.id,
      planTitle: plan.title,
      amountDzd: plan.amountDzd,
      vatRate: 0.0,
      paymentMethod: PaymentMethod.baridimob,
      transactionId: transactionReference.trim(),
      satimApprovalCode: 'BMOB-VAL-${now.millisecondsSinceEpoch.toRadixString(16).toUpperCase()}',
      status: InvoiceStatus.paid,
      issuedAt: now,
      periodStart: now,
      periodEnd: now.add(Duration(days: plan.billingPeriodDays)),
    );

    _invoicesByPlace.putIfAbsent(placeId, () => []).add(invoice);

    return PaymentCheckoutResult(
      isSuccess: true,
      orderId: transactionReference,
      approvalCode: invoice.satimApprovalCode,
      invoice: invoice,
    );
  }

  /// Validation du format officiel du Relevé d'Identité Postale (RIP) Algérie Poste (20 chiffres)
  static bool validateAlgerianRip(String rip) {
    if (rip.length != 20) return false;
    final account = BigInt.tryParse(rip.substring(0, 18));
    final key = int.tryParse(rip.substring(18, 20));
    if (account == null || key == null) return false;

    // Clé RIP Algérie Poste : Clé = 97 - (CCP * 100) % 97
    final remainder = (account * BigInt.from(100)) % BigInt.from(97);
    final expectedKey = 97 - remainder.toInt();
    return key == expectedKey;
  }
}
