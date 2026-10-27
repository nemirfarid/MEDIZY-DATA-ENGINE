/// Modèle représentant un médicament du répertoire pharmaceutique national algérien (DCI & Spécialités).
class DzMedication {
  final int id;
  final String nomCommercial;
  final String dci; // Dénomination Commune Internationale
  final String dosage;
  final String forme;
  final String laboratoire;
  final bool remboursableChifa;
  final double? prixDzd;
  final bool isPrinceps; // Vrai si médicament princeps (référence), Faux si générique

  const DzMedication({
    required this.id,
    required this.nomCommercial,
    required this.dci,
    required this.dosage,
    required this.forme,
    required this.laboratoire,
    this.remboursableChifa = true,
    this.prixDzd,
    this.isPrinceps = false,
  });

  factory DzMedication.fromMap(Map<String, dynamic> map) {
    return DzMedication(
      id: map['id'] as int? ?? (map['rowid'] as int? ?? 0),
      nomCommercial: (map['nom_commercial'] as String?)?.trim() ?? '',
      dci: (map['dci'] as String?)?.trim() ?? '',
      dosage: (map['dosage'] as String?)?.trim() ?? '',
      forme: (map['forme'] as String?)?.trim() ?? '',
      laboratoire: (map['laboratoire'] as String?)?.trim() ?? '',
      remboursableChifa: (map['remboursable_chifa'] is int)
          ? (map['remboursable_chifa'] as int) == 1
          : (map['remboursable_chifa'] as bool? ?? true),
      prixDzd: (map['prix_dzd'] != null)
          ? (map['prix_dzd'] as num).toDouble()
          : null,
      isPrinceps: (map['is_princeps'] is int)
          ? (map['is_princeps'] as int) == 1
          : (map['is_princeps'] as bool? ?? false),
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'nom_commercial': nomCommercial,
      'dci': dci,
      'dosage': dosage,
      'forme': forme,
      'laboratoire': laboratoire,
      'remboursable_chifa': remboursableChifa ? 1 : 0,
      'prix_dzd': prixDzd,
      'is_princeps': isPrinceps ? 1 : 0,
    };
  }

  /// Indique si le laboratoire est un producteur national algérien (ex: Saidal, Biopharm)
  bool get isLocalProducer {
    final lab = laboratoire.toLowerCase();
    return lab.contains('saidal') ||
        lab.contains('biopharm') ||
        lab.contains('sophal') ||
        lab.contains('merinal') ||
        lab.contains('inpha') ||
        lab.contains('frater') ||
        lab.contains('salem') ||
        lab.contains('bekd') ||
        lab.contains('hupp');
  }

  /// Libellé complet formaté pour l'affichage (ex: "Doliprane 1 000 mg - Comprimé")
  String get fullTitle => '$nomCommercial $dosage ($forme)';

  DzMedication copyWith({
    int? id,
    String? nomCommercial,
    String? dci,
    String? dosage,
    String? forme,
    String? laboratoire,
    bool? remboursableChifa,
    double? prixDzd,
    bool? isPrinceps,
  }) {
    return DzMedication(
      id: id ?? this.id,
      nomCommercial: nomCommercial ?? this.nomCommercial,
      dci: dci ?? this.dci,
      dosage: dosage ?? this.dosage,
      forme: forme ?? this.forme,
      laboratoire: laboratoire ?? this.laboratoire,
      remboursableChifa: remboursableChifa ?? this.remboursableChifa,
      prixDzd: prixDzd ?? this.prixDzd,
      isPrinceps: isPrinceps ?? this.isPrinceps,
    );
  }
}

/// Résultat du regroupement d'équivalence DCI & Génériques
class DciEquivalenceResult {
  final String searchedQuery;
  final String dci;
  final DzMedication? targetMedication;
  final List<DzMedication> allEquivalents;
  final List<DzMedication> generics;
  final List<DzMedication> princepsList;
  final List<DzMedication> localProducers;

  const DciEquivalenceResult({
    required this.searchedQuery,
    required this.dci,
    this.targetMedication,
    required this.allEquivalents,
    required this.generics,
    required this.princepsList,
    required this.localProducers,
  });

  bool get hasEquivalents => allEquivalents.isNotEmpty;
  int get count => allEquivalents.length;
}
