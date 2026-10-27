
/// Modèle officiel d'un établissement de santé qualifié - Santé DZ / Medizy
class HealthFacility {
  final int id;
  final String? placeId;
  final String nom;
  final String categorie;
  final String wilaya;
  final String wilayaCode;
  final String commune;
  final String? adresse;
  final String? telephone;
  final String? siteWeb;
  final double? note;
  final int? nombreAvis;
  final double latitude;
  final double longitude;
  final String? source;
  double? distanceKm;

  HealthFacility({
    required this.id,
    this.placeId,
    required this.nom,
    required this.categorie,
    required this.wilaya,
    required this.wilayaCode,
    required this.commune,
    this.adresse,
    this.telephone,
    this.siteWeb,
    this.note,
    this.nombreAvis,
    required this.latitude,
    required this.longitude,
    this.source,
    this.distanceKm,
  });

  /// Création depuis un tuple de base de données SQLite
  factory HealthFacility.fromMap(Map<String, dynamic> map) {
    return HealthFacility(
      id: map['id'] is num ? (map['id'] as num).toInt() : int.parse(map['id'].toString()),
      placeId: map['place_id'] as String?,
      nom: (map['nom'] as String?) ?? 'Établissement Sanitaire',
      categorie: (map['categorie'] as String?) ?? 'Santé',
      wilaya: (map['wilaya'] as String?) ?? '',
      wilayaCode: (map['wilaya_code'] as String?) ?? '',
      commune: (map['commune'] as String?) ?? '',
      adresse: map['adresse'] as String?,
      telephone: map['telephone'] as String?,
      siteWeb: map['site_web'] as String?,
      note: map['note'] != null
          ? (map['note'] is num ? (map['note'] as num).toDouble() : double.tryParse(map['note'].toString()))
          : null,
      nombreAvis: map['nombre_avis'] != null
          ? (map['nombre_avis'] is num ? (map['nombre_avis'] as num).toInt() : int.tryParse(map['nombre_avis'].toString()))
          : null,
      latitude: map['latitude'] is num
          ? (map['latitude'] as num).toDouble()
          : double.parse(map['latitude'].toString()),
      longitude: map['longitude'] is num
          ? (map['longitude'] as num).toDouble()
          : double.parse(map['longitude'].toString()),
      source: map['source'] as String?,
      distanceKm: map['distance_km'] != null
          ? (map['distance_km'] is num ? (map['distance_km'] as num).toDouble() : double.tryParse(map['distance_km'].toString()))
          : null,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'place_id': placeId,
      'nom': nom,
      'categorie': categorie,
      'wilaya': wilaya,
      'wilaya_code': wilayaCode,
      'commune': commune,
      'adresse': adresse,
      'telephone': telephone,
      'site_web': siteWeb,
      'note': note,
      'nombre_avis': nombreAvis,
      'latitude': latitude,
      'longitude': longitude,
      'source': source,
      if (distanceKm != null) 'distance_km': distanceKm,
    };
  }

  /// Indique si l'établissement assure des urgences, une garde ou un service 24/24
  bool get isEmergencyOrOnDuty {
    final lowerNom = nom.toLowerCase();
    final lowerCat = categorie.toLowerCase();
    return lowerNom.contains('urgenc') ||
        lowerNom.contains('garde') ||
        lowerNom.contains('24/24') ||
        lowerNom.contains('chu') ||
        lowerNom.contains('eph') ||
        lowerNom.contains('hopital') ||
        lowerNom.contains('hôpital') ||
        lowerCat.contains('hopital') ||
        lowerCat.contains('polyclinique') ||
        lowerCat.contains('urgence');
  }

  /// Indique si l'établissement est conventionné Chifa (ضمان اجتماعي CNAS/CASNOS)
  bool get hasChifa {
    final cat = categorie.toLowerCase();
    final name = nom.toLowerCase();
    return cat.contains('pharmacie') ||
        cat.contains('laboratoire') ||
        cat.contains('imagerie') ||
        cat.contains('radiolog') ||
        cat.contains('clinique') ||
        cat.contains('hôpital') ||
        cat.contains('hopital') ||
        cat.contains('polyclinique') ||
        cat.contains('centre de santé') ||
        cat.contains('santé') ||
        name.contains('chifa') ||
        name.contains('cnas') ||
        name.contains('casnos');
  }

  /// Numéro national nettoyé pour composition téléphonique
  String? get callNumber {
    if (telephone == null || telephone!.trim().isEmpty) return null;
    return telephone!.replaceAll(RegExp(r'[^0-9+]'), '');
  }

  /// Coordonnées WGS84 formatées
  String get wgs84Coordinates => '$latitude, $longitude';

  /// Texte complet pour partage
  String get shareText {
    final sb = StringBuffer();
    sb.writeln('$nom ($categorie)');
    sb.writeln('$commune, Wilaya de $wilaya ($wilayaCode)');
    if (adresse != null && adresse!.isNotEmpty) sb.writeln('Adresse : $adresse');
    if (telephone != null && telephone!.isNotEmpty) sb.writeln('Tél : $telephone');
    sb.writeln('Position GPS : $wgs84Coordinates');
    sb.writeln('https://maps.google.com/?q=$latitude,$longitude');
    return sb.toString();
  }
}
