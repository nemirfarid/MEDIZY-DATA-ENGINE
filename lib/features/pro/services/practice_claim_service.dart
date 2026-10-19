import 'dart:math';
import '../models/practice_profile.dart';

/// Service de revendication de fiches sanitaires Medizy Pro.
/// Transforme les 35 832 fiches pré-remplies en canal d'acquisition client direct.
class PracticeClaimService {
  final Map<int, PracticeProfile> _profiles = {};

  /// Récupère ou instancie le profil associé à un placeId de la base de données
  PracticeProfile getOrCreateProfile({
    required int placeId,
    required String establishmentName,
    required String specialty,
    required String wilayaCode,
    required String commune,
    required String officialPhone,
  }) {
    return _profiles.putIfAbsent(
      placeId,
      () => PracticeProfile(
        placeId: placeId,
        establishmentName: establishmentName,
        specialty: specialty,
        wilayaCode: wilayaCode,
        commune: commune,
        officialPhone: officialPhone,
      ),
    );
  }

  /// Étape 1 : Initier la revendication par le praticien
  String initiateClaim({
    required int placeId,
    required String practitionerName,
    required String nationalIdOrOrderNumber,
  }) {
    final profile = _profiles[placeId];
    if (profile == null) {
      throw StateError('Profil sanitaire introuvable pour placeId: $placeId');
    }

    if (profile.isClaimed && profile.verificationStatus == ClaimVerificationStatus.verified) {
      throw StateError('Cet établissement a déjà été revendiqué et certifié.');
    }

    // Génération d'un code OTP sécurisé à 6 chiffres
    final rnd = Random();
    final otp = (100000 + rnd.nextInt(900000)).toString();

    profile.practitionerName = practitionerName;
    profile.nationalIdOrOrderNumber = nationalIdOrOrderNumber;
    profile.verificationCode = otp;
    profile.verificationStatus = ClaimVerificationStatus.pendingValidation;

    return otp;
  }

  /// Étape 2 : Validation du code OTP et activation de l'essai gratuit Medizy Pro 30 jours
  bool verifyClaim({
    required int placeId,
    required String verificationCode,
  }) {
    final profile = _profiles[placeId];
    if (profile == null) return false;

    if (profile.verificationCode == verificationCode.trim()) {
      profile.isClaimed = true;
      profile.verificationStatus = ClaimVerificationStatus.verified;
      profile.isTrialActive = true;
      profile.trialEndsAt = DateTime.now().add(const Duration(days: 30));
      return true;
    }

    return false;
  }

  /// Vérifie si un profil est éligible à l'utilisation de Medizy Pro
  bool isAuthorizedForPro(int placeId) {
    final profile = _profiles[placeId];
    if (profile == null) return false;
    return profile.isClaimed && profile.hasActiveAccess;
  }
}
