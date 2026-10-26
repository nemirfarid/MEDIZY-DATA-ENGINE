import 'package:test/test.dart';
import 'package:sante_dz_medizy/features/pro/models/medical_ticket.dart';
import 'package:sante_dz_medizy/features/pro/models/practice_profile.dart';
import 'package:sante_dz_medizy/features/pro/controllers/virtual_queue_controller.dart';
import 'package:sante_dz_medizy/features/pro/services/practice_claim_service.dart';

void main() {
  group('MEDIZY PRO — MODULE FILE D\'ATTENTE VIRTUELLE & REVENDICATION B2B', () {
    const testPlaceId = 1042;
    late VirtualQueueController queueController;
    late PracticeClaimService claimService;

    setUp(() {
      queueController = VirtualQueueController(
        placeId: testPlaceId,
        standardConsultationMinutes: 15,
      );
      claimService = PracticeClaimService();
    });

    test('1. Émission de ticket virtuel et anonymisation du numéro de téléphone', () {
      final t1 = queueController.takeTicket(
        patientAlias: 'M. Benali',
        phone: '0550 12 34 56',
        appointmentType: AppointmentType.walkIn,
      );

      expect(t1.ticketNumber, equals(1));
      expect(t1.placeId, equals(testPlaceId));
      expect(t1.status, equals(TicketStatus.waiting));
      // Vérification du hachage sécurisé (Loi 18-07)
      expect(t1.patientPhoneHash, isNot(contains('0550123456')));
      expect(t1.patientPhoneHash.length, equals(16));

      final t2 = queueController.takeTicket(
        patientAlias: 'Mme. Mansouri',
        phone: '0661 98 76 54',
      );
      expect(t2.ticketNumber, equals(2));
      expect(queueController.allTickets.length, equals(2));
    });

    test('2. Triage d\'urgence et priorité absolue en salle d\'attente', () {
      // Patient 1 : consultation normale
      queueController.takeTicket(patientAlias: 'Patient Routine 1', isUrgent: false);
      // Patient 2 : consultation normale
      queueController.takeTicket(patientAlias: 'Patient Routine 2', isUrgent: false);
      // Patient 3 : Urgence pédiatrique / vitale
      final urgentTicket = queueController.takeTicket(patientAlias: 'Enfant détresse respiratoire', isUrgent: true);

      // Le premier appelé doit être l'urgence, quel que soit l'ordre d'arrivée
      final waiting = queueController.waitingTickets;
      expect(waiting.first.ticketNumber, equals(urgentTicket.ticketNumber));
      expect(waiting.first.isUrgent, isTrue);

      final called = queueController.callNext();
      expect(called?.ticketId, equals(urgentTicket.ticketId));
      expect(called?.status, equals(TicketStatus.called));
    });

    test('3. Cycle complet d\'une consultation et mise à jour des heures estimées', () {
      final t1 = queueController.takeTicket(patientAlias: 'P1');
      queueController.takeTicket(patientAlias: 'P2');

      // Appel de P1
      final called = queueController.callNext();
      expect(called?.ticketNumber, equals(1));

      // Entrée en consultation
      final started = queueController.startConsultation(t1.ticketId);
      expect(started, isTrue);
      expect(t1.status, equals(TicketStatus.inConsultation));

      // Fin de consultation
      final completed = queueController.completeConsultation(t1.ticketId);
      expect(completed, isTrue);
      expect(t1.status, equals(TicketStatus.completed));
      expect(queueController.totalCompletedToday, equals(1));

      // État de la file pour P2
      final status = queueController.getQueueStatus();
      expect(status.totalWaiting, equals(1));
      expect(status.totalCompletedToday, equals(1));
    });

    test('4. Gestion des annulations et No-Show', () {
      final t1 = queueController.takeTicket(patientAlias: 'Patient Absent');
      final t2 = queueController.takeTicket(patientAlias: 'Patient Annule');

      queueController.markNoShow(t1.ticketId);
      expect(t1.status, equals(TicketStatus.noShow));

      queueController.cancelTicket(t2.ticketId);
      expect(t2.status, equals(TicketStatus.cancelled));

      expect(queueController.waitingTickets.isEmpty, isTrue);
    });

    test('5. Revendication de fiche pré-remplie et activation de l\'essai gratuit 30 jours', () {
      final profile = claimService.getOrCreateProfile(
        placeId: 502,
        establishmentName: 'Cabinet Dr. Amrani - Cardiologie',
        specialty: 'Cardiologie',
        wilayaCode: '16',
        commune: 'Sidi M\'Hamed',
        officialPhone: '021 66 55 44',
      );

      expect(profile.isClaimed, isFalse);
      expect(profile.verificationStatus, equals(ClaimVerificationStatus.unclaimed));

      // Étape 1 : Initier la revendication
      final otp = claimService.initiateClaim(
        placeId: 502,
        practitionerName: 'Dr. Karim Amrani',
        nationalIdOrOrderNumber: 'ORD-MED-16-8921',
      );

      expect(otp.length, equals(6));
      expect(profile.verificationStatus, equals(ClaimVerificationStatus.pendingValidation));

      // Échec avec mauvais code
      final failed = claimService.verifyClaim(placeId: 502, verificationCode: '000000');
      expect(failed, isFalse);
      expect(profile.isClaimed, isFalse);

      // Succès avec le bon code
      final verified = claimService.verifyClaim(placeId: 502, verificationCode: otp);
      expect(verified, isTrue);
      expect(profile.isClaimed, isTrue);
      expect(profile.isTrialActive, isTrue);
      expect(profile.trialEndsAt, isNotNull);
      expect(profile.trialEndsAt!.isAfter(DateTime.now().add(const Duration(days: 29))), isTrue);
      expect(claimService.isAuthorizedForPro(502), isTrue);
    });
  });
}
