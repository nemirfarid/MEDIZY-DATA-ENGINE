import 'package:flutter/material.dart';
import '../../../../core/services/offline_health_search_service.dart';
import '../../../map/offline_map_view.dart';

/// Grille responsive et épurée de catégories pour la page d'accueil MEDIZY.
/// Présente une seule icône dédiée par catégorie dans un conteneur stylisé
/// avec son libellé court en dessous.
class CategoryGrid extends StatelessWidget {
  final OfflineHealthSearchService searchService;
  final void Function(String categorySlug)? onCategorySelected;

  const CategoryGrid({
    Key? key,
    required this.searchService,
    this.onCategorySelected,
  }) : super(key: key);

  static const List<Map<String, dynamic>> categories = [
    {
      'label': 'Généraliste',
      'icon': Icons.medical_services_rounded,
      'color': Color(0xFF00695C),
      'slug': 'médecin',
    },
    {
      'label': 'Dentiste',
      'icon': Icons.medical_services_outlined,
      'color': Color(0xFF0288D1),
      'slug': 'dentiste',
    },
    {
      'label': 'Pédiatre',
      'icon': Icons.child_care_rounded,
      'color': Color(0xFF00ACC1),
      'slug': 'pédiatrie',
    },
    {
      'label': 'Pharmacie',
      'icon': Icons.local_pharmacy_rounded,
      'color': Color(0xFF2E7D32),
      'slug': 'pharmacie',
    },
    {
      'label': 'Clinique',
      'icon': Icons.local_hospital_rounded,
      'color': Color(0xFF1565C0),
      'slug': 'clinique',
    },
    {
      'label': 'Laboratoire',
      'icon': Icons.science_rounded,
      'color': Color(0xFFEF6C00),
      'slug': 'laboratoire',
    },
    {
      'label': 'Cardiologie',
      'icon': Icons.favorite_rounded,
      'color': Color(0xFFC62828),
      'slug': 'cardiologie',
    },
    {
      'label': 'Imagerie',
      'icon': Icons.scanner_rounded,
      'color': Color(0xFF4527A0),
      'slug': 'imagerie',
    },
    {
      'label': 'Ophtalmo',
      'icon': Icons.visibility_rounded,
      'color': Color(0xFF00897B),
      'slug': 'ophtalmologie',
    },
    {
      'label': 'Gynéco',
      'icon': Icons.female_rounded,
      'color': Color(0xFFAD1457),
      'slug': 'gynécologie',
    },
    {
      'label': 'Urgences',
      'icon': Icons.emergency_rounded,
      'color': Color(0xFFB71C1C),
      'slug': 'urgence',
    },
    {
      'label': 'Paramédical',
      'icon': Icons.healing_rounded,
      'color': Color(0xFF558B2F),
      'slug': 'kinésithérapie',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        // Grille responsive : 4 colonnes sur tablette/écran large (>= 520px), 3 colonnes sur mobile
        final crossAxisCount = constraints.maxWidth >= 520 ? 4 : 3;

        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            mainAxisSpacing: 14,
            crossAxisSpacing: 14,
            childAspectRatio: 0.95,
          ),
          itemCount: categories.length,
          itemBuilder: (context, index) {
            final cat = categories[index];
            return _CategoryItemCard(
              label: cat['label'] as String,
              icon: cat['icon'] as IconData,
              color: cat['color'] as Color,
              onTap: () {
                final slug = cat['slug'] as String;
                if (onCategorySelected != null) {
                  onCategorySelected!(slug);
                } else {
                  _navigateToMapWithCategory(context, slug);
                }
              },
            );
          },
        );
      },
    );
  }

  void _navigateToMapWithCategory(BuildContext context, String slug) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => OfflineMapView(
          searchService: searchService,
          initialCategory: slug,
        ),
      ),
    );
  }
}

class _CategoryItemCard extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _CategoryItemCard({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withValues(alpha: 0.18), width: 1.2),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.08),
              blurRadius: 8,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Conteneur circulaire stylisé avec une seule icône dédiée
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    color.withValues(alpha: 0.15),
                    color.withValues(alpha: 0.28),
                  ],
                ),
                border: Border.all(
                  color: color.withValues(alpha: 0.35),
                  width: 1.5,
                ),
              ),
              child: Center(
                child: Icon(
                  icon,
                  color: color,
                  size: 26,
                ),
              ),
            ),
            const SizedBox(height: 8),
            // Libellé court en dessous
            Text(
              label,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade900,
                letterSpacing: 0.1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
