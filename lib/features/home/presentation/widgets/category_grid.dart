import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../core/services/offline_health_search_service.dart';
import '../map/offline_map_view.dart';

/// Grille ergonomique de catégories pour la page d'accueil MEDIZY.
///
/// Affiche les principales catégories de santé avec icônes distinctes.
/// Clic sur une catégorie : redirection vers l'écran de recherche avec pré-filtrage actif.
class CategoryGrid extends StatelessWidget {
  final OfflineHealthSearchService searchService;

  const CategoryGrid({Key? key, required this.searchService}) : super(key: key);

  static const List<Map<String, dynamic>> categories = [
    {'label': 'Médecins', 'icon': Icons.medical_services, 'color': Color(0xFF00695C), 'slug': 'médecin'},
    {'label': 'Pharmacies', 'icon': Icons.local_pharmacy, 'color': Color(0xFF2E7D32), 'slug': 'pharmacie'},
    {'label': 'Laboratoires', 'icon': Icons.biotech, 'color': Color(0xFF6A1B9A), 'slug': 'laboratoire'},
    {'label': 'Imagerie', 'icon': Icons.scanner, 'color': Color(0xFF1565C0), 'slug': 'imagerie'},
    {'label': 'Cliniques', 'icon': Icons.local_hospital, 'color': Color(0xFFC62828), 'slug': 'clinique'},
    {'label': 'Urgences', 'icon': Icons.emergency, 'color': Color(0xFFD84315), 'slug': 'urgence'},
    {'label': 'Dentistes', 'icon': Icons.medical_services_outlined, 'color': Color(0xFF0277BD), 'slug': 'dentiste'},
    {'label': 'Paramédical', 'icon': Icons.healing, 'color': Color(0xFF558B2F), 'slug': 'kinésithérapie'},
  ];

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 4,
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        childAspectRatio: 0.85,
      ),
      itemCount: categories.length,
      itemBuilder: (context, index) {
        final cat = categories[index];
        return _CategoryTile(
          label: cat['label'] as String,
          icon: cat['icon'] as IconData,
          color: cat['color'] as Color,
          onTap: () => _openCategory(context, cat['slug'] as String),
        );
      },
    );
  }

  void _openCategory(BuildContext context, String slug) {
    // Redirection vers l'écran de recherche avec pré-filtrage actif
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => OfflineMapView(
          searchService: searchService,
          initialCenter: const LatLng(28.0339, 1.6596),
          initialZoom: 5.8,
        ),
      ),
    );
  }
}

class _CategoryTile extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  const _CategoryTile({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 28),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: color.withOpacity(0.9),
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
