enum TriageUrgencyLevel {
  green,  // Consultation programmée / routine
  orange, // Consultation recommandée sous 24h
  red,    // Urgence immédiate / SAMU 15 / Protection Civile 14
}

class TriageOrientationResult {
  final TriageUrgencyLevel urgencyLevel;
  final String urgencyLabel;
  final String adviceMessage;
  final List<String> recommendedSpecialties;
  final bool shouldCallEmergency;
  final String emergencyNumber;
  final List<String> detectedKeywords;

  TriageOrientationResult({
    required this.urgencyLevel,
    required this.urgencyLabel,
    required this.adviceMessage,
    required this.recommendedSpecialties,
    required this.shouldCallEmergency,
    required this.emergencyNumber,
    required this.detectedKeywords,
  });

  Map<String, dynamic> toJson() => {
    'urgencyLevel': urgencyLevel.name,
    'urgencyLabel': urgencyLabel,
    'adviceMessage': adviceMessage,
    'recommendedSpecialties': recommendedSpecialties,
    'shouldCallEmergency': shouldCallEmergency,
    'emergencyNumber': emergencyNumber,
    'detectedKeywords': detectedKeywords,
  };
}

/// Moteur local et souverain d'orientation et de triage symptomatique.
/// Analyse le texte en Français et en Darija algérienne (arabe ou translittérée).
/// STRICTEMENT ORIENTATIF : N'émet AUCUN diagnostic médical ni ordonnance.
class SymptomTriageEngine {
  // Mots-clés d'urgence vitale ROUGE (SAMU 15 / Protection Civile 14)
  static final List<String> _redKeywords = [
    'poitrine', 'douleur poitrine', 'infarctus', 'coeur serre', 'bras gauche',
    'difficulte respirer', 'etouffement', 'asphyxie', 'inconscient', 'perte connaissance',
    'coma', 'convulsion', 'hemorragie', 'saignement abondant', 'avc', 'paralysie',
    'visage deforme', 'parole trouble', 'chute tension', 'choc anaphylactique',
    // Darija algérienne (Arabe & Translittéré)
    'صدري', 'وجع في صدري', 'سطار في قلبي', 'قلبي يوجع', 'فقد الوعي', 'غيبوبة',
    'ما يقدرش يتنفس', 'خنقة', 'دم بزاف', 'سطار حاد', 'فالج', 'شلل',
    'sedri', 'sedri yewjaani', 'qelbi', 'khnaqa', 'ma yeqderch yetneffes',
    'ghaybouba', 'dem bezaf', 'chtar fi sedri'
  ];

  // Mots-clés de niveau ORANGE (Consultation sous 24h)
  static final List<String> _orangeKeywords = [
    'fievre 39', 'fievre 40', 'forte fievre', 'vomissement repetes', 'fracture',
    'entorse grave', 'brulure', 'plaie profonde', 'crise asthme', 'colique nephretique',
    'douleur rein', 'appendicite', 'mal ventre aigu', 'oeil blesse', 'traumatisme',
    // Darija algérienne
    'حمى قوية', 'سخانة 39', 'سخانة 40', 'تقيؤ بزاف', 'تقيا', 'كسر', 'رجلي مكسورة',
    'وجع كلاوي', 'كرشي تقطع', 'عينيا مجروحة', 'ضربة في الراس',
    'skhana 39', 'skhana 40', 'homma', 'klaoui', 'kerchi toujaa bezaf',
    'teqya', 'rejel meksoura'
  ];

  // Dictionnaire de correspondances sémantiques vers les 102 catégories officielles
  static final Map<String, List<String>> _specialtyMappings = {
    'coeur': ['Cardiologue', 'Chirurgien Cardiovasculaire', 'Médecin Généraliste'],
    'poitrine': ['Cardiologue', 'Pneumologue', 'Urgences'],
    'tension': ['Cardiologue', 'Médecin Généraliste', 'Médecin Interniste'],
    'hta': ['Cardiologue', 'Médecin Généraliste', 'Médecin Interniste'],
    'poumon': ['Pneumologue', 'Phtisiologue', 'Médecin Généraliste'],
    'toux': ['Pneumologue', 'Pédiatre', 'Médecin Généraliste'],
    'asthme': ['Pneumologue', 'Allergologue', 'Pédiatre'],
    'ventre': ['Gastro-Entérologue', 'Chirurgien Général', 'Médecin Généraliste'],
    'estomac': ['Gastro-Entérologue', 'Chirurgien Viscéral', 'Médecin Généraliste'],
    'colon': ['Gastro-Entérologue', 'Proctologue', 'Médecin Interniste'],
    'rein': ['Néphrologue', 'Urologue', 'Médecin Interniste'],
    'urinaire': ['Urologue', 'Néphrologue', 'Gynécologue'],
    'dent': ['Chirurgien Dentiste', 'Orthodontiste', 'Parodontiste'],
    'gencive': ['Chirurgien Dentiste', 'Parodontiste', 'Stomatologue'],
    'enfant': ['Pédiatre', 'Pédopsychiatre', 'Chirurgien Pédiatrique'],
    'nourrisson': ['Pédiatre', 'Néonatologue', 'Médecin Généraliste'],
    'bebe': ['Pédiatre', 'Néonatologue', 'Médecin Généraliste'],
    'grossesse': ['Gynécologue Obstétricien', 'Sage-Femme', 'Échographiste'],
    'femme': ['Gynécologue Obstétricien', 'Sénologue', 'Médecin Généraliste'],
    'oeil': ['Ophtalmologue', 'Opticien', 'Chirurgien Ophtalmologue'],
    'yeux': ['Ophtalmologue', 'Orthoptiste', 'Opticien'],
    'vision': ['Ophtalmologue', 'Orthoptiste', 'Opticien'],
    'peau': ['Dermatologue', 'Allergologue', 'Chirurgien Plastique'],
    'bouton': ['Dermatologue', 'Allergologue', 'Médecin Généraliste'],
    'os': ['Traumatologue Orthopédiste', 'Rhumatologue', 'Kinésithérapeute'],
    'dos': ['Rhumatologue', 'Traumatologue Orthopédiste', 'Kinésithérapeute'],
    'articulation': ['Rhumatologue', 'Traumatologue Orthopédiste', 'Kinésithérapeute'],
    'cerveau': ['Neurologue', 'Neurochirurgien', 'Psychiatre'],
    'tete': ['Neurologue', 'ORL', 'Médecin Généraliste'],
    'migraine': ['Neurologue', 'ORL', 'Médecin Généraliste'],
    'gorge': ['ORL', 'Médecin Généraliste', 'Phoniatre'],
    'oreille': ['ORL', 'Audioprothésiste', 'Médecin Généraliste'],
    'nez': ['ORL', 'Allergologue', 'Médecin Généraliste'],
    'sucre': ['Endocrinologue Diabétologue', 'Nutritionniste', 'Médecin Interniste'],
    'diabete': ['Endocrinologue Diabétologue', 'Nutritionniste', 'Podologue'],
    'thyroide': ['Endocrinologue Diabétologue', 'Chirurgien ORL', 'Médecin Interniste'],
    'sang': ['Hématologue', 'Laboratoire d\'analyses médicales', 'Médecin Interniste'],
    'analyse': ['Laboratoire d\'analyses médicales', 'Médecin Biologiste', 'Médecin Généraliste'],
    'radio': ['Radiologue', 'Centre d\'imagerie médicale', 'Médecin Généraliste'],
    'scanner': ['Radiologue', 'Centre d\'imagerie médicale', 'Neurochirurgien'],
    'irm': ['Radiologue', 'Centre d\'imagerie médicale', 'Neurologue'],
    // Darija
    'ضرسة': ['Chirurgien Dentiste', 'Stomatologue'],
    'اسنان': ['Chirurgien Dentiste', 'Orthodontiste'],
    'عيني': ['Ophtalmologue', 'Opticien'],
    'ودني': ['ORL', 'Audioprothésiste'],
    'كرشي': ['Gastro-Entérologue', 'Chirurgien Général'],
    'ضهري': ['Rhumatologue', 'Traumatologue Orthopédiste', 'Kinésithérapeute'],
    'سطار': ['Médecin Généraliste', 'Médecin Interniste', 'Rhumatologue'],
    'سبيطار': ['Hôpital public', 'Polyclinique', 'Urgences'],
    'طبيب اطفال': ['Pédiatre', 'Médecin Généraliste'],
    'دواء': ['Pharmacie', 'Médecin Généraliste'],
  };

  /// Évalue une description symptomatique libre et renvoie l'orientation prédictive
  TriageOrientationResult evaluateSymptoms(String userInput) {
    if (userInput.trim().isEmpty) {
      return TriageOrientationResult(
        urgencyLevel: TriageUrgencyLevel.green,
        urgencyLabel: 'Consultation programmée',
        adviceMessage: 'Veuillez décrire vos symptômes ou choisir une spécialité médicale.',
        recommendedSpecialties: ['Médecin Généraliste', 'Polyclinique'],
        shouldCallEmergency: false,
        emergencyNumber: '3030',
        detectedKeywords: [],
      );
    }

    final inputLower = userInput.toLowerCase();
    final detectedRed = <String>[];
    final detectedOrange = <String>[];
    final detectedKeywords = <String>[];

    // Vérification Urgence Vitale ROUGE
    for (final kw in _redKeywords) {
      if (inputLower.contains(kw.toLowerCase())) {
        detectedRed.add(kw);
      }
    }

    // Vérification Urgence Modérée ORANGE
    for (final kw in _orangeKeywords) {
      if (inputLower.contains(kw.toLowerCase())) {
        detectedOrange.add(kw);
      }
    }

    // Détermination de la spécialité
    final specialtyScores = <String, int>{};
    _specialtyMappings.forEach((key, list) {
      if (inputLower.contains(key.toLowerCase())) {
        detectedKeywords.add(key);
        for (int i = 0; i < list.length; i++) {
          final spec = list[i];
          final weight = 3 - i; // pondération selon la position
          specialtyScores[spec] = (specialtyScores[spec] ?? 0) + weight;
        }
      }
    });

    final sortedSpecialties = specialtyScores.keys.toList()
      ..sort((a, b) => (specialtyScores[b] ?? 0).compareTo(specialtyScores[a] ?? 0));

    final topSpecialties = sortedSpecialties.take(3).toList();
    if (topSpecialties.isEmpty) {
      topSpecialties.addAll(['Médecin Généraliste', 'Polyclinique', 'Pharmacie']);
    }

    // Décision finale de triage
    if (detectedRed.isNotEmpty) {
      return TriageOrientationResult(
        urgencyLevel: TriageUrgencyLevel.red,
        urgencyLabel: 'URGENCE VITALE IMMÉDIATE',
        adviceMessage:
            'Vos symptômes indiquent une situation critique nécessitant une prise en charge urgente immédiate. Ne prenez pas le volant seul.',
        recommendedSpecialties: ['Urgences Médico-Chirurgicales', 'SAMU', ...topSpecialties],
        shouldCallEmergency: true,
        emergencyNumber: '15', // SAMU Algérie
        detectedKeywords: detectedRed,
      );
    }

    if (detectedOrange.isNotEmpty) {
      return TriageOrientationResult(
        urgencyLevel: TriageUrgencyLevel.orange,
        urgencyLabel: 'Consultation sous 24 heures recommandée',
        adviceMessage:
            'Vos symptômes requièrent une consultation médicale rapide auprès d\'une structure de proximité ou d\'un spécialiste dans les 24 heures.',
        recommendedSpecialties: topSpecialties,
        shouldCallEmergency: false,
        emergencyNumber: '14', // Protection Civile
        detectedKeywords: detectedOrange,
      );
    }

    return TriageOrientationResult(
      urgencyLevel: TriageUrgencyLevel.green,
      urgencyLabel: 'Consultation programmée',
      adviceMessage:
          'Symptômes ne présentant pas de critère de gravité immédiat. Vous pouvez prendre un ticket virtuel ou planifier un rendez-vous.',
      recommendedSpecialties: topSpecialties,
      shouldCallEmergency: false,
      emergencyNumber: '3030', // Numéro Vert Santé Algérie
      detectedKeywords: detectedKeywords,
    );
  }
}
