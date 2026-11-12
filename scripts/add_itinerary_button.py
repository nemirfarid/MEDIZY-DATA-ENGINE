with open('lib/features/map/widgets/facility_detail_sheet.dart', 'r', encoding='utf-8') as f:
    c = f.read()

# Method to open Google Maps Route / Directions
google_maps_method = '''  Future<void> _openGoogleMapsItinerary() async {
    final destLat = widget.facility.latitude;
    final destLon = widget.facility.longitude;
    // URL universelle Google Maps Directions (fonctionne sur app Google Maps et navigateur)
    final urlStr = 'https://www.google.com/maps/dir/?api=1&destination=$destLat,$destLon&travelmode=driving';
    final uri = Uri.parse(urlStr);
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (_) {}
  }
'''

# Dedicated Itinerary Button
itinerary_button = '''          // Bouton Itinéraire Google Maps (Tracé direct depuis votre position)
          SizedBox(
            width: double.infinity,
            height: 46,
            child: ElevatedButton.icon(
              key: const Key('itinerary_google_maps_button'),
              icon: const Icon(Icons.directions_rounded, size: 22, color: Colors.white),
              label: const Text(
                'Itinéraire Google Maps (Tracer la route)',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF1A73E8), // Bleu officiel Google Maps
                foregroundColor: Colors.white,
                elevation: 2,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: _openGoogleMapsItinerary,
            ),
          ),
          const SizedBox(height: 12),
'''

if '_openGoogleMapsItinerary' not in c:
    # Add method
    idx = c.find('Future<void> _openWhatsApp')
    c = c[:idx] + google_maps_method + '\n' + c[idx:]

if 'itinerary_google_maps_button' not in c:
    # Insert button right above the 4 action buttons
    target = '          // Actions directes : 4 boutons uniformes, sans retour à la ligne'
    c = c.replace(target, itinerary_button + target)

with open('lib/features/map/widgets/facility_detail_sheet.dart', 'w', encoding='utf-8') as f:
    f.write(c)

print('Added Google Maps Itinerary button & handler to FacilityDetailSheet!')

