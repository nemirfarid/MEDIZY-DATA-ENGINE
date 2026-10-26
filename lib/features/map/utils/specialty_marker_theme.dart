import 'package:flutter/material.dart';

/// Dictionnaire et thème visuel pour la différenciation des spécialités de santé sur la carte
class SpecialtyMarkerTheme {
  final IconData icon;
  final Color color;
  final String label;

  const SpecialtyMarkerTheme({
    required this.icon,
    required this.color,
    required this.label,
  });

  /// Détermine dynamiquement l'icône et la couleur thématique selon la spécialité et le statut
  static SpecialtyMarkerTheme forCategory(
    String rawCategory, {
    String? facilityName,
    bool isEmergency = false,
  }) {
    if (isEmergency) {
      return const SpecialtyMarkerTheme(
        icon: Icons.emergency_rounded,
        color: Color(0xFFD32F2F), // Rouge vif
        label: 'Urgences & Garde',
      );
    }

    final cat = rawCategory.trim().toLowerCase();
    final name = (facilityName ?? '').trim().toLowerCase();
    final combined = '$cat $name';

    // 1. Pédiatrie : icône enfant / bébé (turquoise / bleu ciel)
    if (combined.contains('pédiatr') ||
        combined.contains('pediatr') ||
        combined.contains('enfant') ||
        combined.contains('nourrisson')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.child_care_rounded,
        color: Color(0xFF00ACC1),
        label: 'Pédiatrie',
      );
    }

    // 2. Dentiste / Stomatologie : icône soins dentaires (cyan)
    if (combined.contains('dentist') ||
        combined.contains('dentaire') ||
        combined.contains('stomatolog') ||
        combined.contains('orthodont')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.medical_services_outlined,
        color: Color(0xFF0288D1),
        label: 'Dentiste',
      );
    }

    // 3. Pharmacie : croix verte / mortier (vert émeraude)
    if (combined.contains('pharmac') || combined.contains('officine')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.local_pharmacy_rounded,
        color: Color(0xFF2E7D32),
        label: 'Pharmacie',
      );
    }

    // 4. Cardiologie : stéthoscope / cœur (rouge)
    if (combined.contains('cardio') || combined.contains('coeur')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.favorite_rounded,
        color: Color(0xFFC62828),
        label: 'Cardiologie',
      );
    }

    // 5. Laboratoire / Analyses : éprouvette / microscope (ambre / orange)
    if (combined.contains('laboratoire') ||
        combined.contains('analyse') ||
        combined.contains('biolog')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.science_rounded,
        color: Color(0xFFEF6C00),
        label: 'Laboratoire',
      );
    }

    // 6. Urgences / Garde : sirène / ambulance (rouge vif)
    if (combined.contains('urgenc') ||
        combined.contains('garde') ||
        combined.contains('24/24') ||
        combined.contains('samu')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.emergency_rounded,
        color: Color(0xFFB71C1C),
        label: 'Urgences',
      );
    }

    // 7. Radiologie / Imagerie médicale : scanner (bleu cobalt / indigo)
    if (combined.contains('imagerie') ||
        combined.contains('radio') ||
        combined.contains('scanner') ||
        combined.contains('irm') ||
        combined.contains('échograph') ||
        combined.contains('echograph')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.scanner_rounded,
        color: Color(0xFF1565C0),
        label: 'Imagerie Médicale',
      );
    }

    // 8. Ophtalmologie : œil / vision (violet / prune)
    if (combined.contains('ophtalmo') ||
        combined.contains('yeux') ||
        combined.contains('vision')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.visibility_rounded,
        color: Color(0xFF6A1B9A),
        label: 'Ophtalmologie',
      );
    }

    // 9. Gynécologie / Maternité : femme enceinte / maternité (rose fuchsia)
    if (combined.contains('gynéco') ||
        combined.contains('gyneco') ||
        combined.contains('maternit') ||
        combined.contains('obstétri') ||
        combined.contains('sage-femme')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.pregnant_woman_rounded,
        color: Color(0xFFAD1457),
        label: 'Gynécologie',
      );
    }

    // 10. Clinique / Hôpital / Polyclinique (bleu marine / indigo)
    if (combined.contains('hopital') ||
        combined.contains('hôpital') ||
        combined.contains('clinique') ||
        combined.contains('polyclinique') ||
        combined.contains('chu') ||
        combined.contains('eph')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.local_hospital_rounded,
        color: Color(0xFF283593),
        label: 'Hôpital / Clinique',
      );
    }

    // 11. Paramédical / Kinésithérapie : soins / rééducation (vert olive)
    if (combined.contains('kiné') ||
        combined.contains('kine') ||
        combined.contains('paraméd') ||
        combined.contains('paramed') ||
        combined.contains('physio') ||
        combined.contains('infirmier')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.healing_rounded,
        color: Color(0xFF558B2F),
        label: 'Paramédical',
      );
    }

    // 12. Médecin généraliste / Spécialiste par défaut : stéthoscope / praticien (Teal médical)
    return const SpecialtyMarkerTheme(
      icon: Icons.medical_services_rounded,
      color: Color(0xFF00695C),
      label: 'Médecin',
    );
  }
}
