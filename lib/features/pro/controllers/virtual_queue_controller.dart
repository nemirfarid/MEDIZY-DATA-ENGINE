import 'dart:math';
import '../models/medical_ticket.dart';

/// Résumé instantané de la file d'attente pour affichage patient et praticien.
class QueueStatusSummary {
  final int placeId;
  final MedicalTicket? currentTicketInConsultation;
  final MedicalTicket? currentCalledTicket;
  final int totalWaiting;
  final int totalCompletedToday;
  final int averageConsultationMinutes;
  final String announcementMessage;

  QueueStatusSummary({
    required this.placeId,
    this.currentTicketInConsultation,
    this.currentCalledTicket,
    required this.totalWaiting,
    required this.totalCompletedToday,
    required this.averageConsultationMinutes,
    required this.announcementMessage,
  });

  Map<String, dynamic> toJson() => {
    'placeId': placeId,
    'currentConsultationNumber': currentTicketInConsultation?.ticketNumber,
    'currentCalledNumber': currentCalledTicket?.ticketNumber,
    'totalWaiting': totalWaiting,
    'totalCompletedToday': totalCompletedToday,
    'averageConsultationMinutes': averageConsultationMinutes,
    'announcementMessage': announcementMessage,
  };
}

/// Contrôleur haute performance de la file d'attente virtuelle Medizy Pro.
/// Résout le point de douleur critique de l'encombrement des salles d'attente.
class VirtualQueueController {
  final int placeId;
  final int standardConsultationMinutes;
  final List<MedicalTicket> _tickets = [];
  int _ticketCounter = 0;

  VirtualQueueController({
    required this.placeId,
    this.standardConsultationMinutes = 15,
  });

  List<MedicalTicket> get allTickets => List.unmodifiable(_tickets);

  List<MedicalTicket> get waitingTickets => _tickets
      .where((t) => t.status == TicketStatus.waiting)
      .toList()
    ..sort((a, b) {
      // Priorité absolue aux urgences vitales / pédiatriques
      if (a.isUrgent && !b.isUrgent) return -1;
      if (!a.isUrgent && b.isUrgent) return 1;
      return a.ticketNumber.compareTo(b.ticketNumber);
    });

  MedicalTicket? get currentCalledTicket {
    final called = _tickets.where((t) => t.status == TicketStatus.called).toList();
    return called.isNotEmpty ? called.last : null;
  }

  MedicalTicket? get currentInConsultationTicket {
    final inCons = _tickets.where((t) => t.status == TicketStatus.inConsultation).toList();
    return inCons.isNotEmpty ? inCons.last : null;
  }

  int get totalCompletedToday => _tickets.where((t) => t.status == TicketStatus.completed).length;

  /// Émission d'un nouveau ticket virtuel pour le patient
  MedicalTicket takeTicket({
    required String patientAlias,
    String? phone,
    bool isUrgent = false,
    AppointmentType appointmentType = AppointmentType.walkIn,
  }) {
    _ticketCounter++;
    final now = DateTime.now();
    final ticketId = 'TCK-${placeId}-${_ticketCounter}-${now.millisecondsSinceEpoch.toRadixString(16)}';
    final phoneHash = MedicalTicket.hashPhone(phone);

    final ticket = MedicalTicket(
      ticketId: ticketId,
      ticketNumber: _ticketCounter,
      placeId: placeId,
      patientAlias: patientAlias,
      patientPhoneHash: phoneHash,
      isUrgent: isUrgent,
      appointmentType: appointmentType,
      createdAt: now,
      status: TicketStatus.waiting,
    );

    // Calcul de l'heure estimée de consultation
    ticket.estimatedConsultationTime = calculateEstimatedTimeFor(ticket);
    _tickets.add(ticket);
    return ticket;
  }

  /// Appel du patient suivant
  MedicalTicket? callNext() {
    final waiting = waitingTickets;
    if (waiting.isEmpty) return null;

    final nextTicket = waiting.first;
    nextTicket.status = TicketStatus.called;
    nextTicket.calledAt = DateTime.now();
    return nextTicket;
  }

  /// Début effectif de la consultation médicale
  bool startConsultation(String ticketId) {
    final index = _tickets.indexWhere((t) => t.ticketId == ticketId);
    if (index == -1) return false;

    // Si une autre consultation était en cours, la marquer comme terminée
    final current = currentInConsultationTicket;
    if (current != null && current.ticketId != ticketId) {
      completeConsultation(current.ticketId);
    }

    _tickets[index].status = TicketStatus.inConsultation;
    _tickets[index].inConsultationAt = DateTime.now();
    return true;
  }

  /// Finalisation de la consultation
  bool completeConsultation(String ticketId) {
    final index = _tickets.indexWhere((t) => t.ticketId == ticketId);
    if (index == -1) return false;

    _tickets[index].status = TicketStatus.completed;
    _tickets[index].completedAt = DateTime.now();

    // Recalculer les heures de passage des patients en attente
    _updateEstimatedTimes();
    return true;
  }

  /// Signalement de non-présentation (No-Show)
  bool markNoShow(String ticketId) {
    final index = _tickets.indexWhere((t) => t.ticketId == ticketId);
    if (index == -1) return false;

    _tickets[index].status = TicketStatus.noShow;
    _updateEstimatedTimes();
    return true;
  }

  /// Annulation du ticket par le patient
  bool cancelTicket(String ticketId) {
    final index = _tickets.indexWhere((t) => t.ticketId == ticketId);
    if (index == -1) return false;

    _tickets[index].status = TicketStatus.cancelled;
    _updateEstimatedTimes();
    return true;
  }

  /// Calcul du nombre de personnes avant un ticket donné
  int getPositionInQueue(int ticketNumber) {
    final waiting = waitingTickets;
    final index = waiting.indexWhere((t) => t.ticketNumber == ticketNumber);
    return index >= 0 ? index + 1 : 0;
  }

  /// Calcul prédictif de l'heure estimée de consultation
  DateTime calculateEstimatedTimeFor(MedicalTicket ticket) {
    final now = DateTime.now();
    final position = getPositionInQueue(ticket.ticketNumber);
    final minutesToAdd = max(1, position) * standardConsultationMinutes;
    return now.add(Duration(minutes: minutesToAdd));
  }

  void _updateEstimatedTimes() {
    for (final t in waitingTickets) {
      t.estimatedConsultationTime = calculateEstimatedTimeFor(t);
    }
  }

  /// Génération de l'état consolidé de la file
  QueueStatusSummary getQueueStatus() {
    final currentCons = currentInConsultationTicket;
    final currentCalled = currentCalledTicket;
    final waitingCount = waitingTickets.length;

    String announcement;
    if (currentCons != null) {
      final hour = currentCons.estimatedConsultationTime != null
          ? "${currentCons.estimatedConsultationTime!.hour.toString().padLeft(2, '0')}h${currentCons.estimatedConsultationTime!.minute.toString().padLeft(2, '0')}"
          : "En cours";
      announcement = "Consultation en cours : N°${currentCons.ticketNumber} ($hour). $waitingCount patient(s) en attente.";
    } else if (currentCalled != null) {
      announcement = "Patient appelé : N°${currentCalled.ticketNumber}. Veuillez vous présenter en salle de soin.";
    } else {
      announcement = waitingCount > 0
          ? "$waitingCount patient(s) en attente. Consultation sur le point de débuter."
          : "Salle d'attente libre. Prise de ticket immédiate disponible.";
    }

    return QueueStatusSummary(
      placeId: placeId,
      currentTicketInConsultation: currentCons,
      currentCalledTicket: currentCalled,
      totalWaiting: waitingCount,
      totalCompletedToday: totalCompletedToday,
      averageConsultationMinutes: standardConsultationMinutes,
      announcementMessage: announcement,
    );
  }
}
