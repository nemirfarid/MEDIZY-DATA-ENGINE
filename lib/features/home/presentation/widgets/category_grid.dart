import '../../../../core/services/medizy_locale.dart';
import 'package:flutter/material.dart';
import '../../../../core/services/offline_health_search_service.dart';
import '../../../../core/theme/medizy_theme.dart';
import '../../../map/offline_map_view.dart';

/// Grille responsive premium de catégories pour la page d'accueil MEDIZY.
/// Chaque carte affiche le logo Medizy coloré par spécialité + nom (FR/AR avec abréviation si long)
class CategoryGrid extends StatelessWidget {
  final OfflineHealthSearchService searchService;
  final void Function(String categorySlug)? onCategorySelected;

  const CategoryGrid({
    super.key,
    required this.searchService,
    this.onCategorySelected,
  });

  static const List<Map<String, dynamic>> categories = [
    {
      'label': 'Généraliste',
      'slug': 'généraliste',
      'color': MedizyTheme.primary,
      'icon': Icons.medical_services_rounded,
    },
    {
      'label': 'Dentiste',
      'slug': 'dentiste',
      'color': Color(0xFF0288D1),
      'icon': Icons.sentiment_very_satisfied_rounded,
    },
    {
      'label': 'Pédiatre',
      'slug': 'pédiatre',
      'color': Color(0xFF00ACC1),
      'icon': Icons.child_care_rounded,
    },
    {
      'label': 'Pharmacie',
      'slug': 'pharmacie',
      'color': MedizyTheme.success,
      'icon': Icons.medication_rounded,
    },
    {
      'label': 'Clinique',
      'slug': 'clinique',
      'color': Color(0xFF1565C0),
      'icon': Icons.domain_rounded,
    },
    {
      'label': 'Laboratoire',
      'slug': 'laboratoire',
      'color': MedizyTheme.warning,
      'icon': Icons.science_rounded,
    },
    {
      'label': 'Cardiologue',
      'slug': 'cardiologue',
      'color': Color(0xFFC62828),
      'icon': Icons.favorite_rounded,
    },
    {
      'label': 'Imagerie / Radio',
      'slug': 'imagerie',
      'color': Color(0xFF4527A0),
      'icon': Icons.scanner_rounded,
    },
    {
      'label': 'Ophtalmologue',
      'slug': 'ophtalmologue',
      'color': Color(0xFF00897B),
      'icon': Icons.visibility_rounded,
    },
    {
      'label': 'Gynécologue',
      'slug': 'gynécologue',
      'color': MedizyTheme.accent,
      'icon': Icons.female_rounded,
    },
    {
      'label': 'Dermatologue',
      'slug': 'dermatologue',
      'color': Color(0xFF8E24AA),
      'icon': Icons.face_retouching_natural_rounded,
    },
    {
      'label': 'Orthopédiste',
      'slug': 'chirurgie orthopédique',
      'color': Color(0xFF3949AB),
      'icon': Icons.accessibility_new_rounded,
    },
    {
      'label': 'Gastro-entérologue',
      'slug': 'gastro-entérologie',
      'color': Color(0xFF00838F),
      'icon': Icons.restaurant_rounded,
    },
    {
      'label': 'Pneumologue',
      'slug': 'pneumologie',
      'color': Color(0xFF0097A7),
      'icon': Icons.air_rounded,
    },
    {
      'label': 'ORL',
      'slug': 'clinique orl',
      'color': Color(0xFF5E35B1),
      'icon': Icons.hearing_rounded,
    },
    {
      'label': 'Psychiatrie',
      'slug': 'psychiatrie',
      'color': Color(0xFF7B1FA2),
      'icon': Icons.psychology_rounded,
    },
    {
      'label': 'Urgences 24/7',
      'slug': 'urgences',
      'color': MedizyTheme.error,
      'icon': Icons.emergency_rounded,
    },
    {
      'label': 'Paramédical',
      'slug': 'kinésithérapie',
      'color': Color(0xFF558B2F),
      'icon': Icons.healing_rounded,
    },
  ];

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = constraints.maxWidth >= 520 ? 4 : 3;

        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          padding: EdgeInsets.symmetric(horizontal: MedizyTheme.spacingM, vertical: MedizyTheme.spacingS),
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
              labelFr: cat['label'] as String,
              labelAr: MedizyLocale.translateCategory(cat['label'] as String),
              abbrAr: MedizyLocale.translateCategory(cat['label'] as String, useAbbr: true),
              slug: cat['slug'] as String,
              color: cat['color'] as Color,
              icon: cat['icon'] as IconData,
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
  final String labelFr;
  final String labelAr;
  final String abbrAr;
  final String slug;
  final Color color;
  final IconData icon;
  final VoidCallback onTap;

  const _CategoryItemCard({
    required this.labelFr,
    required this.labelAr,
    required this.abbrAr,
    required this.slug,
    required this.color,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isArabic = MedizyLocale.isArabic;

    // Choisir le texte à afficher : FR, AR complet, ou AR abrégé si trop long
    String displayLabel;
    if (!isArabic) {
      displayLabel = labelFr;
    } else {
      // Si le texte arabe est long (>14 chars), utiliser l'abréviation
      displayLabel = labelAr.length > 14 ? abbrAr : labelAr;
    }

    return TweenAnimationBuilder<double>(
      duration: Duration(milliseconds: 300 + (slug.hashCode % 5) * 50),
      tween: Tween(begin: 0.0, end: 1.0),
      curve: Curves.easeOutCubic,
      builder: (context, value, child) {
        return Transform.scale(
          scale: 0.9 + 0.1 * value,
          child: Opacity(
            opacity: value,
            child: child,
          ),
        );
      },
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusL),
        child: Container(
          decoration: BoxDecoration(
            color: MedizyTheme.surface,
            borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusL),
            border: Border.all(color: color.withValues(alpha: 0.18), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: color.withValues(alpha: 0.1),
                blurRadius: 12,
                offset: const Offset(0, 4),
                spreadRadius: 0,
              ),
              BoxShadow(
                color: MedizyTheme.shadowColor,
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white,
                color.withValues(alpha: 0.02),
              ],
            ),
          ),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Conteneur circulaire avec logo Medizy coloré
              Hero(
                tag: 'category_$slug',
                child: Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: MedizyTheme.categoryGradient(color),
                    border: Border.all(
                      color: color.withValues(alpha: 0.4),
                      width: 2,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: color.withValues(alpha: 0.25),
                        blurRadius: 8,
                        offset: const Offset(0, 3),
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                  child: Center(
                    child: ColorFiltered(
                      colorFilter: ColorFilter.mode(
                        color,
                        BlendMode.srcIn,
                      ),
                      child: Image.asset(
                        'assets/images/medizy_logo.png',
                        width: 36,
                        height: 36,
                        fit: BoxFit.contain,
                        errorBuilder: (context, error, stackTrace) {
                          return Icon(icon, color: color, size: 28);
                        },
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: MedizyTheme.spacingS + 2),
              // Libellé avec gestion FR/AR + abréviation
              Flexible(
                child: Text(
                  displayLabel,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                    color: MedizyTheme.textPrimary,
                    letterSpacing: 0.2,
                    fontFamily: 'Cairo',
                    height: 1.2,
                  ),
                ),
              ),
              // Petit indicateur de spécialité (point coloré)
              const SizedBox(height: 4),
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}