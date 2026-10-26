import 'package:meta/meta.dart';

/// Représentation immuable d'une Wilaya algérienne (Découpage administratif national)
@immutable
class Wilaya {
  final String code; // Code officiel à 2 chiffres (ex: "01", "16", "31")
  final String name; // Nom officiel (ex: "Adrar", "Alger", "Oran")
  final int totalFacilities;

  const Wilaya({
    required this.code,
    required this.name,
    this.totalFacilities = 0,
  });

  factory Wilaya.fromMap(Map<String, Object?> map) {
    return Wilaya(
      code: (map['wilaya_code'] ?? map['code'] ?? '').toString().padLeft(2, '0'),
      name: (map['wilaya'] ?? map['name'] ?? '').toString(),
      totalFacilities: _parseInt(map['total_facilities'] ?? map['count']),
    );
  }

  Map<String, Object?> toMap() {
    return {
      'code': code,
      'name': name,
      'total_facilities': totalFacilities,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Wilaya &&
          runtimeType == other.runtimeType &&
          code == other.code &&
          name == other.name;

  @override
  int get hashCode => code.hashCode ^ name.hashCode;

  @override
  String toString() => 'Wilaya($code - $name, structures: $totalFacilities)';

  static int _parseInt(Object? value) {
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }
}

/// Représentation immuable d'une Commune algérienne rattachée à sa Wilaya
@immutable
class Commune {
  final String name;
  final String wilayaCode;
  final int totalFacilities;

  const Commune({
    required this.name,
    required this.wilayaCode,
    this.totalFacilities = 0,
  });

  factory Commune.fromMap(Map<String, Object?> map) {
    return Commune(
      name: (map['commune'] ?? map['name'] ?? '').toString(),
      wilayaCode: (map['wilaya_code'] ?? map['code'] ?? '').toString().padLeft(2, '0'),
      totalFacilities: _parseInt(map['total_facilities'] ?? map['count']),
    );
  }

  Map<String, Object?> toMap() {
    return {
      'name': name,
      'wilaya_code': wilayaCode,
      'total_facilities': totalFacilities,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Commune &&
          runtimeType == other.runtimeType &&
          name == other.name &&
          wilayaCode == other.wilayaCode;

  @override
  int get hashCode => name.hashCode ^ wilayaCode.hashCode;

  @override
  String toString() => 'Commune($name, Wilaya: $wilayaCode, structures: $totalFacilities)';

  static int _parseInt(Object? value) {
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }
}
