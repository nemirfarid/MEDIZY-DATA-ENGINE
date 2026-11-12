import '../../../core/services/medizy_locale.dart';
import 'package:flutter/material.dart';
import '../../../core/constants/algeria_wilayas.dart';

/// Sélecteur modal moderne des 58 Wilayas d'Algérie avec recherche instantanée
class WilayaPickerSheet extends StatefulWidget {
  final String? currentSelectedCode;

  const WilayaPickerSheet({Key? key, this.currentSelectedCode}) : super(key: key);

  static Future<WilayaInfo?> show(BuildContext context, {String? currentCode}) {
    return showModalBottomSheet<WilayaInfo?>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => WilayaPickerSheet(currentSelectedCode: currentCode),
    );
  }

  @override
  State<WilayaPickerSheet> createState() => _WilayaPickerSheetState();
}

class _WilayaPickerSheetState extends State<WilayaPickerSheet> {
  String _searchFilter = '';

  @override
  Widget build(BuildContext context) {
    final filteredWilayas = WilayaInfo.allWilayas.where((w) {
      if (_searchFilter.isEmpty) return true;
      final q = _searchFilter.toLowerCase();
      return w.code.contains(q) ||
          w.name.toLowerCase().contains(q) ||
          w.arabicName.contains(q);
    }).toList();

    return Container(
      height: MediaQuery.of(context).size.height * 0.75,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Poignée supérieure
          Container(
            width: 40,
            height: 4,
            margin: EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: Colors.grey.shade300,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // En-tête
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 20, vertical: 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      MedizyLocale.t('Sélectionner une Wilaya', 'اختر ولاية'),
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF0F3B36),
                      ),
                    ),
                    Text(
                      '58 Wilayas d\'Algérie (01 Adrar à 58 El Meniaa)',
                      style: TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ),
                TextButton.icon(
                  onPressed: () => Navigator.pop(context, null), // Réinitialise à Vue Nationale
                  icon: const Icon(Icons.public, size: 18),
                  label: Text(MedizyLocale.t('Toute l\'Algérie (59 658 fiches)', 'كامل الجزائر (59 658 هيكل صحي)')),
                  style: TextButton.styleFrom(foregroundColor: Colors.teal.shade800),
                ),
              ],
            ),
          ),

          // Champ de recherche rapide
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Rechercher par numéro ou nom (ex: 27, Mostaganem)...',
                prefixIcon: const Icon(Icons.search, color: Colors.teal),
                isDense: true,
                filled: true,
                fillColor: Colors.grey.shade100,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
              ),
              onChanged: (val) => setState(() => _searchFilter = val.trim()),
            ),
          ),

          const Divider(height: 1),

          // Liste des 58 Wilayas
          Expanded(
            child: ListView.builder(
              itemCount: filteredWilayas.length,
              itemBuilder: (ctx, idx) {
                final w = filteredWilayas[idx];
                final isSelected = widget.currentSelectedCode == w.code;

                return ListTile(
                  leading: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: isSelected ? Colors.teal.shade800 : Colors.teal.shade50,
                    ),
                    child: Center(
                      child: Text(
                        w.code,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                          color: isSelected ? Colors.white : Colors.teal.shade800,
                        ),
                      ),
                    ),
                  ),
                  title: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        w.name,
                        style: TextStyle(
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                          color: isSelected ? Colors.teal.shade900 : Colors.black87,
                        ),
                      ),
                      Text(
                        w.arabicName,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ),
                  subtitle: Text(
                    'Chef-lieu : ${w.name} (${w.lat.toStringAsFixed(2)}°N, ${w.lon.toStringAsFixed(2)}°E)',
                    style: const TextStyle(fontSize: 11, color: Colors.grey),
                  ),
                  trailing: isSelected
                      ? const Icon(Icons.check_circle, color: Colors.teal)
                      : const Icon(Icons.chevron_right, size: 20, color: Colors.grey),
                  onTap: () => Navigator.pop(context, w),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
