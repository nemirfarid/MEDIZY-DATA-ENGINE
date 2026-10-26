import 'package:meta/meta.dart';
import '../../../core/errors/database_failure.dart';
import '../../../core/models/geo_models.dart';
import '../../../core/models/health_professional.dart';
import '../../../core/models/health_search_filter.dart';

/// Statuts du cycle de vie d'une recherche d'établissements de santé
enum HealthSearchStatus {
  initial,
  loading,
  loadingMore,
  success,
  empty,
  error,
}

/// État immuable du contrôleur de recherche de santé (Offline-First)
@immutable
class HealthSearchState {
  final HealthSearchStatus status;
  final List<HealthProfessional> results;
  final HealthSearchFilter filter;
  final List<Wilaya> availableWilayas;
  final List<Commune> availableCommunes;
  final List<String> availableSpecialties;
  final bool onlyOnDutyPharmacies;
  final double? userLatitude;
  final double? userLongitude;
  final bool hasReachedMax;
  final DatabaseFailure? failure;

  const HealthSearchState({
    this.status = HealthSearchStatus.initial,
    this.results = const [],
    this.filter = const HealthSearchFilter(limit: 20, offset: 0),
    this.availableWilayas = const [],
    this.availableCommunes = const [],
    this.availableSpecialties = const [],
    this.onlyOnDutyPharmacies = false,
    this.userLatitude,
    this.userLongitude,
    this.hasReachedMax = false,
    this.failure,
  });

  bool get isLoading => status == HealthSearchStatus.loading;
  bool get isLoadingMore => status == HealthSearchStatus.loadingMore;
  bool get isSuccess => status == HealthSearchStatus.success;
  bool get isEmpty => status == HealthSearchStatus.empty;
  bool get isError => status == HealthSearchStatus.error;
  bool get hasLocation => userLatitude != null && userLongitude != null;

  HealthSearchState copyWith({
    HealthSearchStatus? status,
    List<HealthProfessional>? results,
    HealthSearchFilter? filter,
    List<Wilaya>? availableWilayas,
    List<Commune>? availableCommunes,
    List<String>? availableSpecialties,
    bool? onlyOnDutyPharmacies,
    double? userLatitude,
    double? userLongitude,
    bool? hasReachedMax,
    DatabaseFailure? failure,
    bool clearUserLocation = false,
    bool clearFailure = false,
  }) {
    return HealthSearchState(
      status: status ?? this.status,
      results: results ?? this.results,
      filter: filter ?? this.filter,
      availableWilayas: availableWilayas ?? this.availableWilayas,
      availableCommunes: availableCommunes ?? this.availableCommunes,
      availableSpecialties: availableSpecialties ?? this.availableSpecialties,
      onlyOnDutyPharmacies: onlyOnDutyPharmacies ?? this.onlyOnDutyPharmacies,
      userLatitude: clearUserLocation ? null : (userLatitude ?? this.userLatitude),
      userLongitude: clearUserLocation ? null : (userLongitude ?? this.userLongitude),
      hasReachedMax: hasReachedMax ?? this.hasReachedMax,
      failure: clearFailure ? null : (failure ?? this.failure),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is HealthSearchState &&
          runtimeType == other.runtimeType &&
          status == other.status &&
          results == other.results &&
          filter == other.filter &&
          onlyOnDutyPharmacies == other.onlyOnDutyPharmacies &&
          userLatitude == other.userLatitude &&
          userLongitude == other.userLongitude &&
          hasReachedMax == other.hasReachedMax &&
          failure == other.failure;

  @override
  int get hashCode =>
      status.hashCode ^
      results.hashCode ^
      filter.hashCode ^
      onlyOnDutyPharmacies.hashCode ^
      userLatitude.hashCode ^
      userLongitude.hashCode ^
      hasReachedMax.hashCode ^
      failure.hashCode;

  @override
  String toString() =>
      'HealthSearchState(status: $status, count: ${results.length}, maxReached: $hasReachedMax, loc: $hasLocation, failure: $failure)';
}
