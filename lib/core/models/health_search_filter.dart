import 'package:meta/meta.dart';

/// DTO immuable spécifiant les critères de recherche dans l'annuaire de santé
@immutable
class HealthSearchFilter {
  final String? wilayaCode;
  final String? commune;
  final String? specialty;
  final String? query;
  final bool onlyChifa;
  final int limit;
  final int offset;

  const HealthSearchFilter({
    this.wilayaCode,
    this.commune,
    String? specialty,
    String? category,
    this.query,
    this.onlyChifa = false,
    this.limit = 50,
    this.offset = 0,
  })  : specialty = category ?? specialty,
        assert(limit > 0 && limit <= 500, 'La limite doit être comprise entre 1 et 500'),
        assert(offset >= 0, "L'offset doit être positif ou nul");

  String? get category => specialty;

  HealthSearchFilter copyWith({
    String? wilayaCode,
    String? commune,
    String? specialty,
    String? category,
    String? query,
    bool? onlyChifa,
    int? limit,
    int? offset,
    bool clearWilayaCode = false,
    bool clearCommune = false,
    bool clearSpecialty = false,
    bool clearCategory = false,
    bool clearQuery = false,
  }) {
    return HealthSearchFilter(
      wilayaCode: clearWilayaCode ? null : (wilayaCode ?? this.wilayaCode),
      commune: clearCommune ? null : (commune ?? this.commune),
      specialty: (clearSpecialty || clearCategory) ? null : (category ?? specialty ?? this.specialty),
      query: clearQuery ? null : (query ?? this.query),
      onlyChifa: onlyChifa ?? this.onlyChifa,
      limit: limit ?? this.limit,
      offset: offset ?? this.offset,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is HealthSearchFilter &&
          runtimeType == other.runtimeType &&
          wilayaCode == other.wilayaCode &&
          commune == other.commune &&
          specialty == other.specialty &&
          query == other.query &&
          onlyChifa == other.onlyChifa &&
          limit == other.limit &&
          offset == other.offset;

  @override
  int get hashCode =>
      wilayaCode.hashCode ^
      commune.hashCode ^
      specialty.hashCode ^
      query.hashCode ^
      onlyChifa.hashCode ^
      limit.hashCode ^
      offset.hashCode;

  @override
  String toString() =>
      'HealthSearchFilter(wilaya: $wilayaCode, commune: $commune, spec: $specialty, q: "$query", chifa: $onlyChifa, limit: $limit, offset: $offset)';
}
