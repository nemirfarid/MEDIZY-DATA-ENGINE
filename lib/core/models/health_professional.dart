import 'package:meta/meta.dart';

/// Modèle immuable et strictement typé d'un professionnel ou établissement de santé
@immutable
class HealthProfessional {
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
  final double? distanceKm;

  const HealthProfessional({
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

  /// Création depuis une ligne de résultat SQLite
  factory HealthProfessional.fromRow(Map<String, Object?> row) {
    return HealthProfessional(
      id: _parseInt(row['id']),
      placeId: row['place_id'] as String?,
      nom: (row['nom'] as String?)?.trim() ?? 'Professionnel / Établissement',
      categorie: (row['categorie'] as String?)?.trim() ?? 'Santé',
      wilaya: (row['wilaya'] as String?)?.trim() ?? '',
      wilayaCode: (row['wilaya_code'] as String?)?.trim().padLeft(2, '0') ?? '',
      commune: (row['commune'] as String?)?.trim() ?? '',
      adresse: (row['adresse'] as String?)?.trim(),
      telephone: (row['telephone'] as String?)?.trim(),
      siteWeb: (row['site_web'] as String?)?.trim(),
      note: _parseDouble(row['note']),
      nombreAvis: _parseIntOrNull(row['nombre_avis']),
      latitude: _parseDouble(row['latitude']) ?? 0.0,
      longitude: _parseDouble(row['longitude']) ?? 0.0,
      source: row['source'] as String?,
      distanceKm: _parseDouble(row['distance_km']),
    );
  }

  Map<String, Object?> toMap() {
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

  /// Retourne une nouvelle instance avec les champs spécifiés modifiés (immuabilité)
  HealthProfessional copyWith({
    int? id,
    String? placeId,
    String? nom,
    String? categorie,
    String? wilaya,
    String? wilayaCode,
    String? commune,
    String? adresse,
    String? telephone,
    String? siteWeb,
    double? note,
    int? nombreAvis,
    double? latitude,
    double? longitude,
    String? source,
    double? distanceKm,
  }) {
    return HealthProfessional(
      id: id ?? this.id,
      placeId: placeId ?? this.placeId,
      nom: nom ?? this.nom,
      categorie: categorie ?? this.categorie,
      wilaya: wilaya ?? this.wilaya,
      wilayaCode: wilayaCode ?? this.wilayaCode,
      commune: commune ?? this.commune,
      adresse: adresse ?? this.adresse,
      telephone: telephone ?? this.telephone,
      siteWeb: siteWeb ?? this.siteWeb,
      note: note ?? this.note,
      nombreAvis: nombreAvis ?? this.nombreAvis,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      source: source ?? this.source,
      distanceKm: distanceKm ?? this.distanceKm,
    );
  }

  /// Indique si l'établissement assure des urgences ou une garde médicale
  bool get isEmergency {
    final lowerNom = nom.toLowerCase();
    final lowerCat = categorie.toLowerCase();
    return lowerNom.contains('urgenc') ||
        lowerNom.contains('garde') ||
        lowerNom.contains('24/24') ||
        lowerNom.contains('chu') ||
        lowerNom.contains('eph') ||
        lowerCat.contains('hopital') ||
        lowerCat.contains('polyclinique') ||
        lowerCat.contains('urgence');
  }

  /// Numéro de téléphone nettoyé pour appel direct
  String? get cleanPhoneNumber {
    if (telephone == null || telephone!.trim().isEmpty) return null;
    return telephone!.replaceAll(RegExp(r'[^0-9+]'), '');
  }

  /// Coordonnées WGS84 formatées
  String get coordinatesFormatted => '$latitude, $longitude';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is HealthProfessional &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'HealthProfessional(id: $id, nom: "$nom", cat: "$categorie", wilaya: "$wilayaCode - $wilaya", commune: "$commune")';

  static int _parseInt(Object? value) {
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static int? _parseIntOrNull(Object? value) {
    if (value == null) return null;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  static double? _parseDouble(Object? value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }
}
