import 'package:test/test.dart';
import 'package:sante_dz_medizy/core/ai/symptom_triage_engine.dart';
import 'package:sante_dz_medizy/features/health_book/models/family_health_record.dart';

void main() {
  group('TRIAGE IA SOUVERAIN (FR/DARIJA) & CARNET DE SANTÉ FAMILIAL', () {
    late SymptomTriageEngine triageEngine;

    setUp(() {
      triageEngine = SymptomTriageEngine();
    });

    test('1. Triage d\'urgence vitale ROUGE en Français (Douleur thoracique)', () {
      final result = triageEngine.evaluateSymptoms('Douleur aiguë poitrine gauche avec essoufflement');

      expect(result.urgencyLevel, equals(TriageUrgencyLevel.red));
      expect(result.shouldCallEmergency, isTrue);
      expect(result.emergencyNumber, equals('15')); // SAMU
      expect(result.recommendedSpecialties, contains('Cardiologue'));
      expect(result.urgencyLabel, contains('URGENCE VITALE'));
    });

    test('2. Triage d\'urgence vitale ROUGE en Darija algérienne (عندي سطار حاد في صدري)', () {
      final result = triageEngine.evaluateSymptoms('عندي سطار حاد في صدري و ما نقدرش نتنفس');

      expect(result.urgencyLevel, equals(TriageUrgencyLevel.red));
      expect(result.shouldCallEmergency, isTrue);
      expect(result.emergencyNumber, equals('15'));
      expect(result.detectedKeywords.isNotEmpty, isTrue);
    });

    test('3. Triage d\'urgence modérée ORANGE (Forte fièvre enfant sous 24h)', () {
      final result = triageEngine.evaluateSymptoms('Enfant fievre 39 depuis ce matin avec toux');

      expect(result.urgencyLevel, equals(TriageUrgencyLevel.orange));
      expect(result.shouldCallEmergency, isFalse);
      expect(result.recommendedSpecialties, contains('Pédiatre'));
      expect(result.urgencyLabel, contains('24 heures'));
    });

    test('4. Triage de routine VERT en Darija (Chirurgien dentiste)', () {
      final result = triageEngine.evaluateSymptoms('ضرستني ضرسة العقل حاب نروح لطبيب اسنان');

      expect(result.urgencyLevel, equals(TriageUrgencyLevel.green));
      expect(result.shouldCallEmergency, isFalse);
      expect(result.recommendedSpecialties, contains('Chirurgien Dentiste'));
    });

    test('5. Carnet de santé familial et calendrier vaccinal national algérien', () {
      final birthDate = DateTime(2026, 1, 15);
      final childRecord = FamilyHealthRecord.createNewbornRecord(
        recordId: 'REC-DZ-2026-001',
        childName: 'Inès Benali',
        birthDate: birthDate,
        bloodGroup: 'O+',
      );

      expect(childRecord.vaccines.length, equals(6));
      expect(childRecord.vaccines[0].vaccineName, contains('BCG'));
      expect(childRecord.vaccines[1].targetAge, equals('2 mois'));
      expect(childRecord.vaccines[3].vaccineName, contains('ROR'));

      // Ajout d'une mesure de glycémie
      childRecord.glycemiaLogs.add(
        GlycemiaEntry(
          valueMgDl: 95.0,
          context: 'a_jeun',
          recordedAt: DateTime.now(),
        ),
      );
      expect(childRecord.glycemiaLogs.first.isNormal, isTrue);

      // Ajout d'une mesure tensionnelle normale
      childRecord.bloodPressureLogs.add(
        BloodPressureEntry(
          systolic: 120,
          diastolic: 80,
          pulse: 72,
          recordedAt: DateTime.now(),
        ),
      );
      expect(childRecord.bloodPressureLogs.first.isHypertensive, isFalse);
    });
  });
}
