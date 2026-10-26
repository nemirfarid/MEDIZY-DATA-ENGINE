import 'package:flutter/material.dart';
import '../../../../core/models/health_professional.dart';
import '../../../../core/models/pharmacy.dart';

/// Card de présentation d'un établissement ou professionnel de santé
class HealthProfessionalCard extends StatelessWidget {
  final HealthProfessional professional;
  final VoidCallback onTap;
  final VoidCallback? onCallPressed;
  final bool isFavorite;
  final VoidCallback? onFavoriteToggle;

  const HealthProfessionalCard({
    super.key,
    required this.professional,
    required this.onTap,
    this.onCallPressed,
    this.isFavorite = false,
    this.onFavoriteToggle,
  });

  @override
  Widget build(BuildContext context) {
    final isPharma = professional is Pharmacy;
    final isOnDuty = (isPharma && (professional as Pharmacy).isOnDuty) || professional.isEmergency;
    final acceptsChifa = isPharma ? (professional as Pharmacy).acceptsChifa : true;
    final distance = professional.distanceKm;
    final isClose = distance != null && distance < 5.0;

    return Card(
      key: Key('facility_card_${professional.id}'),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      elevation: 0.5,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: isOnDuty ? Colors.red.shade200 : Colors.grey.shade200,
          width: isOnDuty ? 1.5 : 1.0,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. En-tête : Nom et icône d'action appel
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: _getCategoryColor().withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      _getCategoryIcon(),
                      color: _getCategoryColor(),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          professional.nom,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Colors.black87,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 3),
                        Text(
                          professional.categorie.toUpperCase(),
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.4,
                            color: _getCategoryColor(),
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (onFavoriteToggle != null)
                    IconButton(
                      key: Key('card_fav_button_${professional.id}'),
                      icon: Icon(
                        isFavorite ? Icons.star : Icons.star_border,
                        color: isFavorite ? Colors.amber.shade700 : Colors.grey.shade400,
                      ),
                      iconSize: 22,
                      tooltip: isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris',
                      onPressed: onFavoriteToggle,
                    ),
                  if (professional.telephone != null && professional.telephone!.isNotEmpty)
                    IconButton(
                      key: Key('card_call_button_${professional.id}'),
                      icon: const Icon(Icons.phone_in_talk, color: Colors.teal),
                      iconSize: 22,
                      tooltip: 'Appel direct',
                      onPressed: onCallPressed,
                    ),
                ],
              ),
              const SizedBox(height: 10),

              // 2. Localisation administrative (Commune, Wilaya)
              Row(
                children: [
                  Icon(Icons.location_on_outlined, size: 16, color: Colors.grey.shade600),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      '${professional.commune}, Wilaya de ${professional.wilaya} (${professional.wilayaCode})',
                      style: TextStyle(fontSize: 12.5, color: Colors.grey.shade700),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // 3. Barre de Badges visuels (Proximité, Chifa, Garde/Urgence)
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: [
                  // Badge de proximité relative
                  if (distance != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: isClose ? const Color(0xFFE8F5E9) : Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: isClose ? const Color(0xFF2E7D32) : Colors.grey.shade300,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.near_me,
                            size: 13,
                            color: isClose ? const Color(0xFF2E7D32) : Colors.grey.shade700,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '$distance km',
                            style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.bold,
                              color: isClose ? const Color(0xFF2E7D32) : Colors.grey.shade800,
                            ),
                          ),
                        ],
                      ),
                    ),

                  // Badge Conventionné Chifa
                  if (isPharma && acceptsChifa)
                    Container(
                      key: Key('badge_chifa_${professional.id}'),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE3F2FD),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFF1976D2)),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.verified, size: 13, color: Color(0xFF1976D2)),
                          SizedBox(width: 4),
                          Text(
                            'Chifa CNAS/CASNOS',
                            style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF0D47A1),
                            ),
                          ),
                        ],
                      ),
                    ),

                  // Badge Garde 24/24 / Urgences
                  if (isOnDuty)
                    Container(
                      key: Key('badge_duty_${professional.id}'),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFEBEE),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFFC62828)),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.alarm, size: 13, color: Color(0xFFC62828)),
                          SizedBox(width: 4),
                          Text(
                            'Garde / Urgences',
                            style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFFB71C1C),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getCategoryColor() {
    final cat = professional.categorie.toLowerCase();
    if (cat.contains('pharmacie')) return const Color(0xFF2E7D32);
    if (cat.contains('hopital') || cat.contains('clinique') || cat.contains('chu')) {
      return const Color(0xFFC62828);
    }
    if (cat.contains('dentiste')) return const Color(0xFF00695C);
    if (cat.contains('laboratoire')) return const Color(0xFF6A1B9A);
    return const Color(0xFF0277BD);
  }

  IconData _getCategoryIcon() {
    final cat = professional.categorie.toLowerCase();
    if (cat.contains('pharmacie')) return Icons.local_pharmacy;
    if (cat.contains('hopital') || cat.contains('clinique') || cat.contains('chu')) {
      return Icons.local_hospital;
    }
    if (cat.contains('dentiste')) return Icons.medical_services_outlined;
    if (cat.contains('laboratoire')) return Icons.biotech;
    return Icons.person_outline;
  }
}
