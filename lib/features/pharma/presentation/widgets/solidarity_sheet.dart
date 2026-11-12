import 'package:flutter/material.dart';

/// Modèle pour un bon de solidarité (Wasfa Tikafol / Ordonnance Suspendue)
/// Strictement conforme à la Loi 18-11 sanitaire algérienne :
/// - Zéro PII : Aucun nom de patient, aucun diagnostic, aucune ordonnance scannée
/// - Médicaments toujours délivrés neufs et scellés sous contrôle du pharmacien agréé
class SolidarityVoucher {
  final String id; // Token anonyme ex: TIKAFOL-16-A82F
  final String wilaya;
  final String commune;
  final String nomPharmacie;
  final double montantTotalDzd;
  final double montantCollecteDzd;
  final String descriptionBesoin; // Ex: Traitement antibiotique & antipyrétique enfant
  final DateTime dateCreation;
  final bool isCloture;

  const SolidarityVoucher({
    required this.id,
    required this.wilaya,
    required this.commune,
    required this.nomPharmacie,
    required this.montantTotalDzd,
    required this.montantCollecteDzd,
    required this.descriptionBesoin,
    required this.dateCreation,
    this.isCloture = false,
  });

  double get progression => (montantCollecteDzd / montantTotalDzd).clamp(0.0, 1.0);
  double get montantRestant => (montantTotalDzd - montantCollecteDzd).clamp(0.0, double.infinity);
}

/// Modèle pour le prêt solidaire de matériel médical (fauteuil roulant, béquilles, etc.)
class MedicalEquipmentItem {
  final String id;
  final String titre; // Ex: Fauteuil roulant pliable adulte
  final String type; // Prêt solidaire gratuit / Don
  final String wilaya;
  final String commune;
  final String telephoneContact;
  final String etat; // Bon état / Neuf
  final String disponibilite; // Disponible immédiatement

  const MedicalEquipmentItem({
    required this.id,
    required this.titre,
    required this.type,
    required this.wilaya,
    required this.commune,
    required this.telephoneContact,
    required this.etat,
    required this.disponibilite,
  });
}

/// Écran et Feuille modale d'Entraide et Solidarité Sanitaire ("Tikafol")
/// - Respect absolu de la Loi 18-11 (Ordonnance suspendue via pharmacien agréé)
/// - Zéro exposition des données des patients (Tokens anonymes cryptés)
/// - Sans aucun symbole de croix
class SolidaritySheet extends StatefulWidget {
  final String? initialWilaya;

  const SolidaritySheet({
    super.key,
    this.initialWilaya,
  });

  static Future<void> show(BuildContext context, {String? initialWilaya}) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => SolidaritySheet(initialWilaya: initialWilaya),
    );
  }

  @override
  State<SolidaritySheet> createState() => _SolidaritySheetState();
}

class _SolidaritySheetState extends State<SolidaritySheet> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  

  // Exemples de bons solidaires anonymes initiés par des pharmacies partenaires
  final List<SolidarityVoucher> _vouchers = [
    SolidarityVoucher(
      id: 'TIKAFOL-16-8492',
      wilaya: 'Alger',
      commune: 'Bab El Oued',
      nomPharmacie: 'Pharmacie Centrale El Djenina',
      montantTotalDzd: 3200.0,
      montantCollecteDzd: 2000.0,
      descriptionBesoin: 'Prescription pédiatrique (Antibiotique générique + sirop)',
      dateCreation: DateTime.now().subtract(const Duration(hours: 3)),
    ),
    SolidarityVoucher(
      id: 'TIKAFOL-31-1044',
      wilaya: 'Oran',
      commune: 'Es Senia',
      nomPharmacie: 'Pharmacie Ibn Sina',
      montantTotalDzd: 4800.0,
      montantCollecteDzd: 4800.0,
      descriptionBesoin: 'Traitement hypertension artérielle (1 mois)',
      dateCreation: DateTime.now().subtract(const Duration(hours: 8)),
      isCloture: true,
    ),
    SolidarityVoucher(
      id: 'TIKAFOL-25-3921',
      wilaya: 'Constantine',
      commune: 'El Khroub',
      nomPharmacie: 'Pharmacie Essalam',
      montantTotalDzd: 5600.0,
      montantCollecteDzd: 1800.0,
      descriptionBesoin: 'Insuline humaine & bandelettes de glycémie',
      dateCreation: DateTime.now().subtract(const Duration(hours: 12)),
    ),
    SolidarityVoucher(
      id: 'TIKAFOL-09-7712',
      wilaya: 'Blida',
      commune: 'Boufarik',
      nomPharmacie: 'Pharmacie Errahma',
      montantTotalDzd: 2400.0,
      montantCollecteDzd: 900.0,
      descriptionBesoin: 'Collyre ophtalmique post-opératoire',
      dateCreation: DateTime.now().subtract(const Duration(hours: 24)),
    ),
  ];

  // Matériel médical solidaire (prêt gratuit légal)
  final List<MedicalEquipmentItem> _equipments = [
    const MedicalEquipmentItem(
      id: 'EQ-16-01',
      titre: 'Fauteuil roulant adulte pliable',
      type: 'Prêt solidaire gratuit',
      wilaya: 'Alger',
      commune: 'Hussein Dey',
      telephoneContact: '0550 XX XX XX',
      etat: 'Très bon état',
      disponibilite: 'Disponible',
    ),
    const MedicalEquipmentItem(
      id: 'EQ-31-02',
      titre: 'Paire de béquilles anglaises adulte',
      type: 'Don gracieux',
      wilaya: 'Oran',
      commune: 'Bir El Djir',
      telephoneContact: '0661 XX XX XX',
      etat: 'Comme neuf',
      disponibilite: 'Disponible',
    ),
    const MedicalEquipmentItem(
      id: 'EQ-06-03',
      titre: 'Lit médicalisé manuel avec matelas',
      type: 'Prêt temporaire',
      wilaya: 'Béjaïa',
      commune: 'Akbou',
      telephoneContact: '0770 XX XX XX',
      etat: 'Bon état de marche',
      disponibilite: 'Disponible',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  void _showDonationDialog(SolidarityVoucher voucher) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Container(
              padding: EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.teal.shade50,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(Icons.volunteer_activism_rounded, color: Colors.teal.shade700, size: 24),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Parrainer ce bon',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Réf : ${voucher.id}',
              style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey.shade700, fontSize: 13),
            ),
            const SizedBox(height: 4),
            Text(
              'Pharmacie : ${voucher.nomPharmacie} (${voucher.commune}, ${voucher.wilaya})',
              style: const TextStyle(fontSize: 13, color: Colors.black87),
            ),
            const SizedBox(height: 8),
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.amber.shade200),
              ),
              child: Row(
                children: [
                  Icon(Icons.shield_outlined, color: Colors.amber.shade900, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Reste à couvrir : ${voucher.montantRestant.toStringAsFixed(0)} DZD\n(Médicaments neufs scellés délivrés par le pharmacien)',
                      style: TextStyle(fontSize: 12, color: const Color(0xFF451A03), height: 1.3),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Montant de votre contribution (DZD) :',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [500, 1000, 2000, voucher.montantRestant.toInt()].map((amount) {
                return ActionChip(
                  label: Text('$amount DZD'),
                  backgroundColor: Colors.teal.shade50,
                  labelStyle: TextStyle(color: Colors.teal.shade900, fontWeight: FontWeight.bold, fontSize: 12),
                  onPressed: () {
                    Navigator.of(ctx).pop();
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        backgroundColor: Colors.teal.shade800,
                        content: Row(
                          children: [
                            const Icon(Icons.check_circle_outline_rounded, color: Colors.white),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'Engagement de $amount DZD validé pour la pharmacie partenaire !',
                                style: const TextStyle(fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                );
              }).toList(),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Fermer', style: TextStyle(color: Colors.grey)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.88,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Color(0xFFF8FAFB),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            children: [
              // Poignée de glissement
              Container(
                margin: EdgeInsets.symmetric(vertical: 10),
                width: 44,
                height: 5,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),

              // Header
              Padding(
                padding: EdgeInsets.symmetric(horizontal: 20, vertical: 6),
                child: Row(
                  children: [
                    Container(
                      padding: EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.teal.shade50,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(Icons.volunteer_activism_rounded, color: Colors.teal.shade800, size: 26),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                'Wasfa Tikafol',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.teal.shade900,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.teal.shade700,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: const Text(
                                  'Loi 18-11',
                                  style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ],
                          ),
                          Text(
                            'Ordonnances solidaires & Prêt de matériel (100% Anonyme)',
                            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.arrow_downward_rounded),
                      tooltip: 'Fermer',
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),

              // Onglets
              Container(
                margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade200,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: TabBar(
                  controller: _tabController,
                  indicator: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    color: Colors.teal.shade800,
                  ),
                  labelColor: Colors.white,
                  unselectedLabelColor: Colors.grey.shade700,
                  labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  tabs: const [
                    Tab(
                      icon: Icon(Icons.medication_rounded, size: 18),
                      text: 'Ordonnances Suspendues',
                    ),
                    Tab(
                      icon: Icon(Icons.accessible_forward_rounded, size: 18),
                      text: 'Matériel Médical',
                    ),
                  ],
                ),
              ),

              // Contenu des onglets
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    // Onglet 1 : Ordonnances Suspendues (Wasfa Tikafol)
                    _buildVouchersTab(scrollController),

                    // Onglet 2 : Prêt de matériel médical
                    _buildEquipmentTab(scrollController),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildVouchersTab(ScrollController scrollController) {
    return ListView(
      controller: scrollController,
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      children: [
        // Carte d'information cadre légal & éthique
        Container(
          margin: EdgeInsets.only(bottom: 12),
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.teal.shade50,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.teal.shade200),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.verified_user_outlined, color: Colors.teal.shade800, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Garantie de Sécurité & Anonymat Total',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: Colors.teal.shade900),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      'Pour préserver la dignité des patients et respecter la réglementation sanitaire (Loi 18-11), les médicaments sont financés directement au comptoir de la pharmacie conventionnée. Aucun médicament usagé ni ordonnance nominative n\'est partagé.',
                      style: TextStyle(fontSize: 11, color: Colors.teal.shade900, height: 1.35),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        // Liste des bons
        ..._vouchers.map((voucher) {
          final isDone = voucher.isCloture;
          return Container(
            margin: EdgeInsets.only(bottom: 12),
            padding: EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: isDone ? Colors.green.shade200 : Colors.grey.shade200),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.03),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: isDone ? Colors.green.shade50 : Colors.teal.shade50,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        voucher.id,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: isDone ? Colors.green.shade800 : Colors.teal.shade800,
                        ),
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: isDone ? Colors.green.shade100 : Colors.amber.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        isDone ? 'Complété' : 'En cours',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: isDone ? Colors.green.shade900 : Colors.amber.shade900,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  voucher.descriptionBesoin,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.domain_rounded, size: 14, color: Colors.grey.shade600),
                    const SizedBox(width: 4),
                    Text(
                      '${voucher.nomPharmacie} • ${voucher.commune} (${voucher.wilaya})',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                    ),
                  ],
                ),
                const SizedBox(height: 12),

                // Barre de progression
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: voucher.progression,
                    minHeight: 8,
                    backgroundColor: Colors.grey.shade200,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      isDone ? Colors.green.shade600 : Colors.teal.shade700,
                    ),
                  ),
                ),
                const SizedBox(height: 6),

                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Collecté : ${voucher.montantCollecteDzd.toStringAsFixed(0)} DZD',
                      style: TextStyle(fontSize: 11.5, color: Colors.grey.shade700, fontWeight: FontWeight.w500),
                    ),
                    Text(
                      'Objectif : ${voucher.montantTotalDzd.toStringAsFixed(0)} DZD',
                      style: TextStyle(fontSize: 11.5, color: Colors.teal.shade900, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),

                if (!isDone) ...[
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    height: 38,
                    child: ElevatedButton.icon(
                      onPressed: () => _showDonationDialog(voucher),
                      icon: const Icon(Icons.volunteer_activism_rounded, size: 16),
                      label: const Text(
                        'Participer au règlement de l\'ordonnance',
                        style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.bold),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.teal.shade700,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          );
        }),
      ],
    );
  }

  Widget _buildEquipmentTab(ScrollController scrollController) {
    return ListView(
      controller: scrollController,
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      children: [
        Container(
          margin: EdgeInsets.only(bottom: 12),
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.blue.shade50,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.blue.shade200),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.info_outline_rounded, color: Colors.blue.shade800, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Prêt Solidaire de Matériel Médical',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12.5, color: Colors.blue.shade900),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      'Le matériel médical (non soumis à prescription de molécules chimiques) peut être prêté ou donné légalement entre citoyens ou associations pour aider les personnes à mobilité réduite.',
                      style: TextStyle(fontSize: 11, color: Colors.blue.shade900, height: 1.35),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        ..._equipments.map((eq) {
          return Container(
            margin: EdgeInsets.only(bottom: 12),
            padding: EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.grey.shade200),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.03),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.teal.shade50,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        eq.type,
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.teal.shade800),
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.green.shade50,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        eq.disponibilite,
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.green.shade800),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  eq.titre,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.location_on_outlined, size: 14, color: Colors.grey.shade600),
                    const SizedBox(width: 4),
                    Text(
                      '${eq.commune} (${eq.wilaya}) • État : ${eq.etat}',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  height: 38,
                  child: OutlinedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          backgroundColor: Colors.teal.shade800,
                          content: Text('Contact direct pour ${eq.titre} à ${eq.commune}'),
                        ),
                      );
                    },
                    icon: const Icon(Icons.phone_rounded, size: 16),
                    label: const Text('Contacter pour convenir du prêt'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.teal.shade800,
                      side: BorderSide(color: Colors.teal.shade700),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }
}

