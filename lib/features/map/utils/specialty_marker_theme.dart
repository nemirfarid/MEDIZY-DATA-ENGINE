import 'package:flutter/material.dart';

/// Dictionnaire et thème visuel pour la différenciation des spécialités de santé sur la carte
/// STRICT ZERO CROSS RULE : Aucune croix (Icons.close, Icons.clear, Icons.local_hospital)
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
    String? activeFilterCategory,
  }) {
    // Si un filtre de catégorie est activement sélectionné par l'utilisateur (ex: 'clinique'),
    // tous les marqueurs résultants adoptent STRICTEMENT le thème visuel de cette catégorie !
    if (activeFilterCategory != null && activeFilterCategory.isNotEmpty) {
      final active = activeFilterCategory.trim().toLowerCase();
      if (active.contains('clinique') || active.contains('hopital') || active.contains('hôpital')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.domain_rounded,
          color: Color(0xFF1565C0),
          label: 'Clinique & Hôpital',
        );
      }
      if (active.contains('dentist') || active.contains('dentaire')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.sentiment_very_satisfied_rounded,
          color: Color(0xFF0288D1),
          label: 'Dentiste',
        );
      }
      if (active.contains('pédiatr') || active.contains('pediatr')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.child_care_rounded,
          color: Color(0xFF00ACC1),
          label: 'Pédiatre',
        );
      }
      if (active.contains('pharmac')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.medication_rounded,
          color: Color(0xFF2E7D32),
          label: 'Pharmacie',
        );
      }
      if (active.contains('laboratoire') || active.contains('analyse')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.science_rounded,
          color: Color(0xFFEF6C00),
          label: 'Laboratoire',
        );
      }
      if (active.contains('cardio')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.favorite_rounded,
          color: Color(0xFFC62828),
          label: 'Cardiologue',
        );
      }
      if (active.contains('ophtalm')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.visibility_rounded,
          color: Color(0xFF00897B),
          label: 'Ophtalmologue',
        );
      }
      if (active.contains('gynéco') || active.contains('gyneco')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.female_rounded,
          color: Color(0xFFAD1457),
          label: 'Gynécologue',
        );
      }
      if (active.contains('généralist') || active.contains('generalist')) {
        return const SpecialtyMarkerTheme(
          icon: Icons.medical_services_rounded,
          color: Color(0xFF00695C),
          label: 'Généraliste',
        );
      }
    }

    if (isEmergency) {
      return const SpecialtyMarkerTheme(
        icon: Icons.emergency_rounded,
        color: Color(0xFFB71C1C), // Rouge vif urgences
        label: 'Urgences & Garde',
      );
    }

    final cat = rawCategory.trim().toLowerCase();
    final name = (facilityName ?? '').trim().toLowerCase();
    final combined = '$cat $name';

    // 1. Urgences / Garde : icône emergency (zéro croix)
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

    // 2. Dentiste / Stomatologie : icône sourire / dentaire (sans aucune forme de croix)
    if (combined.contains('dentist') ||
        combined.contains('dentaire') ||
        combined.contains('stomatolog') ||
        combined.contains('orthodont') ||
        combined.contains('أسنان')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.sentiment_very_satisfied_rounded,
        color: Color(0xFF0288D1),
        label: 'Dentiste',
      );
    }

    // 3. Pédiatrie : icône enfant / bébé (turquoise)
    if (combined.contains('pédiatr') ||
        combined.contains('pediatr') ||
        combined.contains('enfant') ||
        combined.contains('nourrisson')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.child_care_rounded,
        color: Color(0xFF00ACC1),
        label: 'Pédiatre',
      );
    }

    // 4. Pharmacie : caducée / médicament vert (vert émeraude)
    if (combined.contains('pharmac') || combined.contains('officine')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.medication_rounded,
        color: Color(0xFF2E7D32),
        label: 'Pharmacie',
      );
    }

    // 5. Cardiologie : cœur (rouge)
    if (combined.contains('cardio') || combined.contains('coeur')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.favorite_rounded,
        color: Color(0xFFC62828),
        label: 'Cardiologie',
      );
    }

    // 6. Laboratoire / Analyses : éprouvette / science (ambre / orange)
    if (combined.contains('laboratoire') ||
        combined.contains('analyse') ||
        combined.contains('biolog')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.science_rounded,
        color: Color(0xFFEF6C00),
        label: 'Laboratoire',
      );
    }

    // 7. Radiologie / Imagerie médicale : scanner (violet foncé)
    if (combined.contains('imagerie') ||
        combined.contains('radio') ||
        combined.contains('scanner') ||
        combined.contains('irm') ||
        combined.contains('échograph') ||
        combined.contains('echograph')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.scanner_rounded,
        color: Color(0xFF4527A0),
        label: 'Imagerie Médicale',
      );
    }

    // 8. Ophtalmologie / Opticien : œil / vision (vert canard / teal)
    if (combined.contains('ophtalmo') ||
        combined.contains('yeux') ||
        combined.contains('vision') ||
        combined.contains('opticien')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.visibility_rounded,
        color: Color(0xFF00897B),
        label: 'Ophtalmologue',
      );
    }

    // 9. Gynécologie / Maternité : femme / maternité (rose fuchsia)
    if (combined.contains('gynéco') ||
        combined.contains('gyneco') ||
        combined.contains('maternit') ||
        combined.contains('obstétri') ||
        combined.contains('sage-femme')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.female_rounded,
        color: Color(0xFFAD1457),
        label: 'Gynécologue',
      );
    }

    // 10. Dermatologie : visage / soin de la peau (violet clair)
    if (combined.contains('dermat')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.face_retouching_natural_rounded,
        color: Color(0xFF8E24AA),
        label: 'Dermatologue',
      );
    }

    // 11. Orthopédie / Traumatologie : silhouette posture (indigo)
    if (combined.contains('orthopéd') ||
        combined.contains('orthoped') ||
        combined.contains('traumato')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.accessibility_new_rounded,
        color: Color(0xFF3949AB),
        label: 'Orthopédiste',
      );
    }

    // 12. Gastro-entérologie : digestion / nutrition (cyan foncé)
    if (combined.contains('gastro')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.restaurant_rounded,
        color: Color(0xFF00838F),
        label: 'Gastro-entérologue',
      );
    }

    // 13. Pneumologie : respiration / air (cyan clair)
    if (combined.contains('pneumo') || combined.contains('respirat')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.air_rounded,
        color: Color(0xFF0097A7),
        label: 'Pneumologue',
      );
    }

    // 14. ORL (Oto-Rhino-Laryngologie) : ouïe / oreille (violet profond)
    if (combined.contains('orl') ||
        combined.contains('rhino') ||
        combined.contains('laryngo') ||
        combined.contains('audio')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.hearing_rounded,
        color: Color(0xFF5E35B1),
        label: 'ORL',
      );
    }

    // 15. Psychiatrie / Psychologie : esprit / psychologie (magenta)
    if (combined.contains('psych')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.psychology_rounded,
        color: Color(0xFF7B1FA2),
        label: 'Psychiatrie',
      );
    }

    // 16. Paramédical / Kinésithérapie : soins / rééducation (vert olive)
    if (combined.contains('kiné') ||
        combined.contains('kine') ||
        combined.contains('paraméd') ||
        combined.contains('paramed') ||
        combined.contains('physio') ||
        combined.contains('infirmier') ||
        combined.contains('orthophon')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.healing_rounded,
        color: Color(0xFF558B2F),
        label: 'Paramédical',
      );
    }

    // 17. Clinique / Hôpital / Polyclinique (bleu cobalt / domaine)
    if (combined.contains('hopital') ||
        combined.contains('hôpital') ||
        combined.contains('clinique') ||
        combined.contains('polyclinique') ||
        combined.contains('chu') ||
        combined.contains('eph')) {
      return const SpecialtyMarkerTheme(
        icon: Icons.domain_rounded,
        color: Color(0xFF1565C0),
        label: 'Clinique / Hôpital',
      );
    }

    // 18. Médecin Généraliste / Praticien par défaut (Teal médical)
    return const SpecialtyMarkerTheme(
      icon: Icons.medical_services_rounded,
      color: Color(0xFF00695C),
      label: 'Généraliste',
    );
  }
}
