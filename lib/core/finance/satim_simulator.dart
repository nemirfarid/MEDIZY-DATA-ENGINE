import 'dart:math';

enum SatimCardType {
  edahabia,
  cib,
  unknown,
}

class SatimAuthorizationResult {
  final bool isSuccess;
  final String orderId;
  final String? approvalCode;
  final String? errorMessage;
  final SatimCardType cardType;
  final String maskedPan;

  SatimAuthorizationResult({
    required this.isSuccess,
    required this.orderId,
    this.approvalCode,
    this.errorMessage,
    required this.cardType,
    required this.maskedPan,
  });
}

/// Simulateur hors-ligne du commutateur monétique national SATIM / GIE Monétique.
/// Permet de valider la conformité des flux CIB et EDAHABIA sans appel bancaire réel.
class SatimSimulator {
  final Map<String, String> _pendingOtps = {}; // orderId -> expectedOtp

  /// Détection automatique du type de carte selon les BINs agréés par SATIM
  static SatimCardType detectCardType(String pan) {
    final cleanPan = pan.replaceAll(RegExp(r'\D'), '');
    if (cleanPan.startsWith('603577') || cleanPan.startsWith('2404') || cleanPan.startsWith('628051')) {
      return SatimCardType.edahabia; // Carte Algérie Poste
    }
    if (cleanPan.startsWith('5354') ||
        cleanPan.startsWith('5211') ||
        cleanPan.startsWith('4000') ||
        cleanPan.startsWith('5130')) {
      return SatimCardType.cib; // Carte Interbancaire SATIM
    }
    return SatimCardType.unknown;
  }

  /// Validation formelle du numéro de carte via l'algorithme de Luhn
  static bool validateLuhn(String pan) {
    final digits = pan.replaceAll(RegExp(r'\D'), '');
    if (digits.length < 16 || digits.length > 19) return false;

    int sum = 0;
    bool alternate = false;
    for (int i = digits.length - 1; i >= 0; i--) {
      int n = int.parse(digits[i]);
      if (alternate) {
        n *= 2;
        if (n > 9) n = (n % 10) + 1;
      }
      sum += n;
      alternate = !alternate;
    }
    return sum % 10 == 0;
  }

  /// Étape 1 : Demande d'autorisation SATIM et génération du challenge 3-D Secure OTP
  SatimAuthorizationResult requestPaymentAuthorization({
    required String pan,
    required String expiryDate, // MM/YY
    required String cvv,
    required double amountDzd,
  }) {
    final cleanPan = pan.replaceAll(RegExp(r'\D'), '');
    final cardType = detectCardType(cleanPan);

    if (cardType == SatimCardType.unknown) {
      return SatimAuthorizationResult(
        isSuccess: false,
        orderId: '',
        errorMessage: 'Carte non reconnue. Seules les cartes CIB et EDAHABIA sont acceptées.',
        cardType: cardType,
        maskedPan: _maskPan(cleanPan),
      );
    }

    if (!validateLuhn(cleanPan)) {
      return SatimAuthorizationResult(
        isSuccess: false,
        orderId: '',
        errorMessage: 'Numéro de carte invalide (échec de vérification Luhn).',
        cardType: cardType,
        maskedPan: _maskPan(cleanPan),
      );
    }

    if (amountDzd <= 0) {
      return SatimAuthorizationResult(
        isSuccess: false,
        orderId: '',
        errorMessage: 'Le montant de transaction doit être supérieur à 0 DZD.',
        cardType: cardType,
        maskedPan: _maskPan(cleanPan),
      );
    }

    final rnd = Random();
    final orderId = 'SAT-${DateTime.now().millisecondsSinceEpoch}-${rnd.nextInt(9999).toString().padLeft(4, '0')}';
    final otp = (100000 + rnd.nextInt(900000)).toString();

    _pendingOtps[orderId] = otp;

    return SatimAuthorizationResult(
      isSuccess: true,
      orderId: orderId,
      cardType: cardType,
      maskedPan: _maskPan(cleanPan),
    );
  }

  /// Récupère l'OTP simulé pour un orderId donné (utile pour les tests automatisés)
  String? getGeneratedOtpForTest(String orderId) => _pendingOtps[orderId];

  /// Étape 2 : Validation du code OTP 3-D Secure et capture bancaire
  SatimAuthorizationResult confirmPaymentWithOtp({
    required String orderId,
    required String enteredOtp,
  }) {
    final expectedOtp = _pendingOtps[orderId];
    if (expectedOtp == null) {
      return SatimAuthorizationResult(
        isSuccess: false,
        orderId: orderId,
        errorMessage: 'Session de paiement SATIM expirée ou inexistante.',
        cardType: SatimCardType.unknown,
        maskedPan: '****',
      );
    }

    if (expectedOtp != enteredOtp.trim()) {
      return SatimAuthorizationResult(
        isSuccess: false,
        orderId: orderId,
        errorMessage: 'Code d\'authentification OTP erroné.',
        cardType: SatimCardType.unknown,
        maskedPan: '****',
      );
    }

    // Capture réussie : émission du code d'approbation SATIM officiel
    _pendingOtps.remove(orderId);
    final rnd = Random();
    final approvalCode = 'SAT-APV-${100000 + rnd.nextInt(900000)}';

    return SatimAuthorizationResult(
      isSuccess: true,
      orderId: orderId,
      approvalCode: approvalCode,
      cardType: SatimCardType.edahabia,
      maskedPan: '****',
    );
  }

  static String _maskPan(String pan) {
    if (pan.length < 8) return '****';
    return '${pan.substring(0, 4)} **** **** ${pan.substring(pan.length - 4)}';
  }
}
