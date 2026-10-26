import 'package:meta/meta.dart';
import 'health_professional.dart';

/// Modèle immuable et spécialisé pour les Officines de Pharmacie en Algérie
@immutable
class Pharmacy extends HealthProfessional {
  final bool isOnDuty;
  final bool acceptsChifa;

  const Pharmacy({
    required super.id,
    super.placeId,
    required super.nom,
    required super.wilaya,
    required super.wilayaCode,
    required super.commune,
    super.adresse,
    super.telephone,
    super.siteWeb,
    super.note,
    super.nombreAvis,
    required super.latitude,
    required super.longitude,
    super.source,
    super.distanceKm,
    this.isOnDuty = false,
    this.acceptsChifa = true,
  }) : super(categorie: 'pharmacie');

  factory Pharmacy.fromRow(Map<String, Object?> row) {
    final base = HealthProfessional.fromRow(row);
    final nomLower = base.nom.toLowerCase();
    final sourceLower = (base.source ?? '').toLowerCase();

    // Détection explicite ou heuristique de garde et conventionnement Chifa
    final bool onDuty;
    if (row.containsKey('is_on_duty') && row['is_on_duty'] != null) {
      final val = row['is_on_duty'];
      onDuty = val == 1 || val == true || val == '1';
    } else {
      onDuty = nomLower.contains('garde') ||
          nomLower.contains('nuit') ||
          nomLower.contains('24/24') ||
          sourceLower.contains('garde');
    }

    final bool chifa;
    if (row.containsKey('accepts_chifa') && row['accepts_chifa'] != null) {
      final val = row['accepts_chifa'];
      chifa = val == 1 || val == true || val == '1';
    } else {
      chifa = true;
    }

    return Pharmacy(
      id: base.id,
      placeId: base.placeId,
      nom: base.nom,
      wilaya: base.wilaya,
      wilayaCode: base.wilayaCode,
      commune: base.commune,
      adresse: base.adresse,
      telephone: base.telephone,
      siteWeb: base.siteWeb,
      note: base.note,
      nombreAvis: base.nombreAvis,
      latitude: base.latitude,
      longitude: base.longitude,
      source: base.source,
      distanceKm: base.distanceKm,
      isOnDuty: onDuty,
      acceptsChifa: chifa,
    );
  }

  @override
  Map<String, Object?> toMap() {
    final map = super.toMap();
    map['is_on_duty'] = isOnDuty ? 1 : 0;
    map['accepts_chifa'] = acceptsChifa ? 1 : 0;
    return map;
  }

  @override
  Pharmacy copyWith({
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
    bool? isOnDuty,
    bool? acceptsChifa,
  }) {
    return Pharmacy(
      id: id ?? this.id,
      placeId: placeId ?? this.placeId,
      nom: nom ?? this.nom,
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
      isOnDuty: isOnDuty ?? this.isOnDuty,
      acceptsChifa: acceptsChifa ?? this.acceptsChifa,
    );
  }

  @override
  String toString() =>
      'Pharmacy(id: $id, nom: "$nom", wilaya: "$wilayaCode - $wilaya", commune: "$commune", garde: $isOnDuty)';
}
