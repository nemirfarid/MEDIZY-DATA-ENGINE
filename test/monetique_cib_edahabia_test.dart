import 'package:test/test.dart';
import 'package:sante_dz_medizy/core/finance/models/subscription_plan.dart';
import 'package:sante_dz_medizy/core/finance/models/invoice.dart';
import 'package:sante_dz_medizy/core/finance/satim_simulator.dart';
import 'package:sante_dz_medizy/core/finance/monetique_gateway.dart';

void main() {
  group('MONÉTIQUE NATIONALE — PASSERELLE CIB, EDAHABIA (SATIM) & BARIDIMOB', () {
    late SatimSimulator simulator;
    late MonetiqueGateway gateway;

    // Numéro de carte EDAHABIA de test valide (Luhn vérifié) : 6035 7700 0000 0004
    const validEdahabiaPan = '6035770000000004';
    // Numéro CIB valide (Luhn vérifié) : 5354 0000 0000 0001
    const validCibPan = '5354000000000001';
    // Numéro de carte invalide
    const invalidPan = '6035770000000002';

    setUp(() {
      simulator = SatimSimulator();
      gateway = MonetiqueGateway(satimSimulator: simulator);
    });

    test('1. Détection des BINs nationaux CIB et EDAHABIA', () {
      expect(SatimSimulator.detectCardType(validEdahabiaPan), equals(SatimCardType.edahabia));
      expect(SatimSimulator.detectCardType(validCibPan), equals(SatimCardType.cib));
      expect(SatimSimulator.detectCardType('4970000000000000'), equals(SatimCardType.unknown));
    });

    test('2. Algorithme de Luhn pour contrôle d\'intégrité de la carte', () {
      expect(SatimSimulator.validateLuhn(validEdahabiaPan), isTrue);
      expect(SatimSimulator.validateLuhn(validCibPan), isTrue);
      expect(SatimSimulator.validateLuhn(invalidPan), isFalse);
    });

    test('3. Cycle complet de paiement SATIM EDAHABIA (Autorisation + OTP + Facturation)', () {
      // Étape 1 : Demande d'autorisation pour Medizy Pro (3 500 DZD)
      final initResult = gateway.initiateCardCheckout(
        placeId: 1042,
        entityName: 'Cabinet Dr. Benali',
        planId: SubscriptionPlan.medizyPro.id,
        pan: validEdahabiaPan,
        expiryDate: '12/28',
        cvv: '123',
      );

      expect(initResult.isSuccess, isTrue);
      expect(initResult.requiresOtp, isTrue);
      expect(initResult.orderId, isNotNull);

      final orderId = initResult.orderId!;

      // Récupération de l'OTP généré par le simulateur
      final expectedOtp = simulator.getGeneratedOtpForTest(orderId);
      expect(expectedOtp, isNotNull);
      expect(expectedOtp!.length, equals(6));

      // Échec si OTP incorrect
      final failResult = gateway.confirmCardCheckout(
        placeId: 1042,
        entityName: 'Cabinet Dr. Benali',
        planId: SubscriptionPlan.medizyPro.id,
        orderId: orderId,
        otp: '999999',
      );
      expect(failResult.isSuccess, isFalse);

      // Succès avec OTP correct
      final successResult = gateway.confirmCardCheckout(
        placeId: 1042,
        entityName: 'Cabinet Dr. Benali',
        planId: SubscriptionPlan.medizyPro.id,
        orderId: orderId,
        otp: expectedOtp,
      );

      expect(successResult.isSuccess, isTrue);
      expect(successResult.approvalCode, startsWith('SAT-APV-'));
      expect(successResult.invoice, isNotNull);

      final invoice = successResult.invoice!;
      expect(invoice.amountDzd, equals(3500.0));
      expect(invoice.formattedAmountDzd, equals('3500.00 DZD'));
      expect(invoice.paymentMethod, equals(PaymentMethod.edahabia));
      expect(invoice.status, equals(InvoiceStatus.paid));
      expect(invoice.nif, isNotNull);
      expect(invoice.satimApprovalCode, startsWith('SAT-APV-'));

      // Vérification de l'historique des factures du cabinet
      final invoices = gateway.getInvoicesForPlace(1042);
      expect(invoices.length, equals(1));
    });

    test('4. Paiement alternatif BaridiMob avec validation du Relevé d\'Identité Postale (RIP)', () {
      // Calcul d'un RIP valide pour compte 007999990000000001
      final account = BigInt.parse('007999990000000001');
      final remainder = (account * BigInt.from(100)) % BigInt.from(97);
      final key = (97 - remainder.toInt()).toString().padLeft(2, '0');
      final validRip = '007999990000000001$key';

      expect(MonetiqueGateway.validateAlgerianRip(validRip), isTrue);
      expect(MonetiqueGateway.validateAlgerianRip('00799999000000000100'), isFalse);

      // Exécution d'un paiement BaridiMob pour Medizy Pharma (2 500 DZD)
      final result = gateway.processBaridiMobCheckout(
        placeId: 7001,
        entityName: 'Pharmacie de la Grande Poste',
        planId: SubscriptionPlan.medizyPharma.id,
        rip: validRip,
        transactionReference: 'BMOB-TXN-20261019-8812',
      );

      expect(result.isSuccess, isTrue);
      expect(result.invoice, isNotNull);
      expect(result.invoice!.amountDzd, equals(2500.0));
      expect(result.invoice!.paymentMethod, equals(PaymentMethod.baridimob));
    });
  });
}
