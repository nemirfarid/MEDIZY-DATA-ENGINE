import 'package:test/test.dart';
import 'package:sante_dz_medizy/features/pharma/models/medication_request.dart';
import 'package:sante_dz_medizy/features/pharma/models/pharmacy_response.dart';
import 'package:sante_dz_medizy/features/pharma/services/dci_catalog_service.dart';
import 'package:sante_dz_medizy/features/pharma/services/dispo_medicament_service.dart';

void main() {
  group('DISPO-MÉDICAMENTS — CATALOGUE DCI, DIFFUSION GÉOLOCALISÉE & CONSOLE OFFICINALE', () {
    late DciCatalogService dciService;
    late DispoMedicamentService dispoService;

    setUp(() {
      dciService = DciCatalogService();
      dispoService = DispoMedicamentService();

      // Enregistrement d'officines partenaires à Alger
      // Pharmacie 1 : Alger Centre (36.7538, 3.0588)
      dispoService.registerPharmacy(
        RegisteredPharmacy(
          placeId: 7001,
          name: 'Pharmacie de la Grande Poste',
          phone: '021 73 11 22',
          commune: 'Alger Centre',
          wilayaCode: '16',
          latitude: 36.7538,
          longitude: 3.0588,
          isDutyNight: true,
        ),
      );

      // Pharmacie 2 : El Biar (36.7690, 3.0290) ~ 3.2 km
      dispoService.registerPharmacy(
        RegisteredPharmacy(
          placeId: 7002,
          name: 'Pharmacie des Martyrs - El Biar',
          phone: '021 92 44 55',
          commune: 'El Biar',
          wilayaCode: '16',
          latitude: 36.7690,
          longitude: 3.0290,
        ),
      );

      // Pharmacie 3 : Boumerdès (36.7600, 3.4700) ~ 37 km (hors du rayon de 10 km)
      dispoService.registerPharmacy(
        RegisteredPharmacy(
          placeId: 7003,
          name: 'Pharmacie du Littoral Boumerdès',
          phone: '024 81 22 33',
          commune: 'Boumerdès',
          wilayaCode: '35',
          latitude: 36.7600,
          longitude: 3.4700,
        ),
      );
    });

    test('1. Recherche dans le catalogue DCI et détection d\'équivalence de marque', () {
      // Recherche par nom de marque commerciale "Augmentin"
      final found = dciService.findByBrandName('Augmentin');
      expect(found, isNotNull);
      expect(found!.dci, contains('Amoxicilline'));
      expect(found.commercialBrands, contains('Augmentin'));

      // Recherche par DCI "Metformine"
      final results = dciService.search('Metformine');
      expect(results.isNotEmpty, isTrue);
      expect(results.first.commercialBrands, contains('Glucophage'));
    });

    test('2. Émission d\'une alerte géolocalisée et ciblage précis des officines (5 à 15 km)', () {
      // Position patient : Place Audin (36.7540, 3.0580)
      final request = dispoService.broadcastMedicationRequest(
        dci: 'Amoxicilline + Acide Clavulanique',
        brandName: 'Augmentin',
        dosage: '1 g',
        form: 'Comprimé',
        latitude: 36.7540,
        longitude: 3.0580,
        radiusKm: 10.0,
        patientSecret: 'PATIENT_KEY_9921',
      );

      expect(request.requestId, startsWith('REQ-MED-'));
      expect(request.patientAnonymityToken, startsWith('ANON-'));
      // L'identité du patient ne doit JAMAIS contenir le secret original (Loi 18-07)
      expect(request.patientAnonymityToken, isNot(contains('PATIENT_KEY_9921')));

      // Vérification du filtrage géographique des pharmacies
      final targeted = dispoService.getTargetedPharmaciesFor(request);
      expect(targeted.length, equals(2)); // Grande Poste + El Biar (dans les 10 km)
      expect(targeted.any((p) => p.placeId == 7003), isFalse); // Boumerdès exclu car > 35 km
    });

    test('3. Console de réponse rapide pharmacien en 1 clic et mise de côté', () {
      final request = dispoService.broadcastMedicationRequest(
        dci: 'Paracétamol',
        dosage: '1 000 mg',
        form: 'Comprimé',
        latitude: 36.7538,
        longitude: 3.0588,
        radiusKm: 10.0,
        patientSecret: 'SECRET_44',
      );

      // Pharmacie 1 répond : DISPONIBLE
      final r1 = dispoService.respondToRequest(
        requestId: request.requestId,
        pharmacyPlaceId: 7001,
        status: AvailabilityStatus.available,
      );
      expect(r1.status, equals(AvailabilityStatus.available));
      expect(r1.holdUntil, isNotNull);
      expect(r1.holdUntil!.isAfter(DateTime.now()), isTrue);

      // Pharmacie 2 répond : ÉQUIVALENT DISPONIBLE
      final r2 = dispoService.respondToRequest(
        requestId: request.requestId,
        pharmacyPlaceId: 7002,
        status: AvailabilityStatus.equivalentAvailable,
        equivalentProposal: 'Efferalgan 1g disponible',
      );
      expect(r2.status, equals(AvailabilityStatus.equivalentAvailable));
      expect(r2.equivalentProposal, equals('Efferalgan 1g disponible'));

      // Consultation des réponses par le patient
      final responses = dispoService.getResponsesForRequest(request.requestId);
      expect(responses.length, equals(2));

      // Réservation du produit auprès de la Pharmacie 1
      final reserved = dispoService.reserveMedication(
        requestId: request.requestId,
        pharmacyPlaceId: 7001,
      );
      expect(reserved, isTrue);
      expect(request.status, equals(MedicationRequestStatus.reserved));
      expect(request.reservedPharmacyPlaceId, equals(7001));
    });

    test('4. Calcul de distance géodésique Haversine instantané (< 1 ms)', () {
      final stopwatch = Stopwatch()..start();
      for (int i = 0; i < 1000; i++) {
        DispoMedicamentService.calculateHaversineDistance(36.7538, 3.0588, 36.7690, 3.0290);
      }
      stopwatch.stop();

      final avgLatencyMs = stopwatch.elapsedMicroseconds / 1000.0 / 1000.0;
      expect(avgLatencyMs, lessThan(0.05)); // Moins de 0,05 ms par calcul Haversine
    });
  });
}
