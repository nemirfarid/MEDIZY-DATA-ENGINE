/// Plans d'abonnement B2B Medizy Pro, Medizy Pharma et Grands Comptes (Cliniques / Imagerie).
class SubscriptionPlan {
  final String id;
  final String title;
  final double amountDzd;
  final int billingPeriodDays;
  final String targetProfession;
  final List<String> features;

  const SubscriptionPlan({
    required this.id,
    required this.title,
    required this.amountDzd,
    this.billingPeriodDays = 30,
    required this.targetProfession,
    required this.features,
  });

  static const medizyPro = SubscriptionPlan(
    id: 'medizy_pro_monthly',
    title: 'Medizy Pro — Praticiens & Spécialistes',
    amountDzd: 3500.0,
    targetProfession: 'Médecins spécialistes, généralistes et dentistes',
    features: [
      'File d\'attente virtuelle intelligente & ticket en temps réel',
      'Réduction de 70% de l\'encombrement physique de la salle d\'attente',
      'Générateur d\'ordonnances sécurisées avec QR Code anti-fraude',
      'Dossier patient informatisé léger et rappels SMS automatisés',
      'Support prioritaire & badge "Profil Vérifié"',
    ],
  );

  static const medizyPharma = SubscriptionPlan(
    id: 'medizy_pharma_monthly',
    title: 'Medizy Pharma — Espace Officinal',
    amountDzd: 2500.0,
    targetProfession: 'Pharmacies d\'officine privées',
    features: [
      'Console en 1 clic pour les demandes Dispo-Médicaments',
      'Badge prioritaire "Pharmacie de Garde" certifiée',
      'Accès à la bourse d\'échange inter-pharmacies de la wilaya',
      'Rapprochement ordonnances numériques',
    ],
  );

  static const medizyClinic = SubscriptionPlan(
    id: 'medizy_clinic_monthly',
    title: 'Medizy Clinique — Établissements & Centres d\'Imagerie',
    amountDzd: 18000.0,
    targetProfession: 'Cliniques privées, centres d\'imagerie et laboratoires',
    features: [
      'Prise de rendez-vous pour examens lourds (IRM, Scanner, Endoscopie)',
      'Multi-salles d\'attente et gestion des flux médico-chirurgicaux',
      'Module de prélèvement biologique à domicile pour laboratoires',
      'Intégration API PACS / Système d\'Information Hospitalier',
    ],
  );

  static List<SubscriptionPlan> get availablePlans => [
    medizyPro,
    medizyPharma,
    medizyClinic,
  ];

  static SubscriptionPlan findById(String planId) {
    return availablePlans.firstWhere(
      (p) => p.id == planId,
      orElse: () => medizyPro,
    );
  }
}
