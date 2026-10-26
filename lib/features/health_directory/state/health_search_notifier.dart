import 'dart:async';
import 'package:flutter/foundation.dart';
import '../../../core/models/geo_models.dart';
import '../../../core/models/pharmacy.dart';
import '../../../core/utils/geo_calculator.dart';
import '../services/health_directory_service.dart';
import 'health_search_state.dart';

/// Contrôleur d'état réactif pour la consultation et le filtrage de l'annuaire de santé
class HealthSearchNotifier extends ChangeNotifier {
  final IHealthDirectoryService _directoryService;
  Timer? _debounceTimer;

  HealthSearchState _state;
  HealthSearchState get state => _state;

  HealthSearchNotifier({
    required IHealthDirectoryService directoryService,
    HealthSearchState initialState = const HealthSearchState(),
  })  : _directoryService = directoryService,
        _state = initialState;

  /// Initialise les données référentielles (Wilayas et Spécialités)
  Future<void> initialize() async {
    final wilayasResult = await _directoryService.getWilayas();
    final specialtiesResult = await _directoryService.getSpecialties();

    List<Wilaya> wilayas = _state.availableWilayas;
    List<String> specialties = _state.availableSpecialties;

    wilayasResult.fold(
      onSuccess: (data) => wilayas = data,
      onFailure: (_) {},
    );

    specialtiesResult.fold(
      onSuccess: (data) => specialties = data,
      onFailure: (_) {},
    );

    _state = _state.copyWith(
      availableWilayas: wilayas,
      availableSpecialties: specialties,
    );
    notifyListeners();
  }

  /// Sélection d'une Wilaya avec réinitialisation de la commune et cascading
  Future<void> setWilaya(String? wilayaCode) async {
    final code = wilayaCode?.trim().padLeft(2, '0');
    if (code == _state.filter.wilayaCode) return;

    List<Commune> newCommunes = const [];

    if (code != null && code.isNotEmpty) {
      final communesResult = await _directoryService.getCommunesForWilaya(code);
      communesResult.fold(
        onSuccess: (data) => newCommunes = data,
        onFailure: (_) {},
      );
    }

    final newFilter = _state.filter.copyWith(
      wilayaCode: code,
      clearWilayaCode: code == null,
      clearCommune: true,
      offset: 0,
    );

    _state = _state.copyWith(
      filter: newFilter,
      availableCommunes: newCommunes,
    );

    await search(isLoadMore: false);
  }

  /// Sélection d'une Commune dépendante de la Wilaya
  Future<void> setCommune(String? commune) async {
    final trimmed = commune?.trim();
    if (trimmed == _state.filter.commune) return;

    final newFilter = _state.filter.copyWith(
      commune: trimmed,
      clearCommune: trimmed == null || trimmed.isEmpty,
      offset: 0,
    );

    _state = _state.copyWith(filter: newFilter);
    await search(isLoadMore: false);
  }

  /// Filtrage par Spécialité ou Catégorie sanitaire
  Future<void> setSpecialty(String? specialty) async {
    final trimmed = specialty?.trim();
    if (trimmed == _state.filter.specialty) return;

    final newFilter = _state.filter.copyWith(
      specialty: trimmed,
      clearSpecialty: trimmed == null || trimmed.isEmpty,
      offset: 0,
    );

    _state = _state.copyWith(filter: newFilter);
    await search(isLoadMore: false);
  }

  /// Bascule du filtre exclusif "Pharmacie de garde"
  Future<void> setOnlyOnDutyPharmacies(bool onlyOnDuty) async {
    if (onlyOnDuty == _state.onlyOnDutyPharmacies) return;

    _state = _state.copyWith(onlyOnDutyPharmacies: onlyOnDuty);
    await search(isLoadMore: false);
  }

  /// Saisie textuelle débouncée à 300 ms (ou paramétrable pour les tests)
  void onSearchQueryChanged(
    String query, {
    Duration debounceDuration = const Duration(milliseconds: 300),
  }) {
    _debounceTimer?.cancel();

    final newFilter = _state.filter.copyWith(
      query: query.trim(),
      offset: 0,
    );

    _state = _state.copyWith(filter: newFilter);

    _debounceTimer = Timer(debounceDuration, () {
      search(isLoadMore: false);
    });
  }

  /// Enregistre la position GPS locale et réordonne instantanément par proximité
  void setUserLocation({required double latitude, required double longitude}) {
    _state = _state.copyWith(
      userLatitude: latitude,
      userLongitude: longitude,
    );

    if (_state.results.isNotEmpty) {
      final sorted = GeoCalculator.sortByProximity(
        _state.results,
        userLatitude: latitude,
        userLongitude: longitude,
      );
      _state = _state.copyWith(results: sorted);
    }

    notifyListeners();
  }

  /// Efface la position GPS et réinitialise le tri
  void clearUserLocation() {
    _state = _state.copyWith(clearUserLocation: true);

    if (_state.results.isNotEmpty) {
      final stripped = _state.results.map((item) {
        return item.copyWith(distanceKm: null);
      }).toList();

      stripped.sort((a, b) => a.nom.compareTo(b.nom));
      _state = _state.copyWith(results: List.unmodifiable(stripped));
    }

    notifyListeners();
  }

  /// Exécute la recherche avec pagination par lot de 20 et tri optionnel
  Future<void> search({bool isLoadMore = false}) async {
    if (isLoadMore) {
      if (_state.hasReachedMax || _state.isLoadingMore) return;
      _state = _state.copyWith(status: HealthSearchStatus.loadingMore);
    } else {
      _state = _state.copyWith(
        status: HealthSearchStatus.loading,
        clearFailure: true,
      );
    }
    notifyListeners();

    final int targetOffset = isLoadMore ? _state.results.length : 0;
    var searchFilter = _state.filter.copyWith(
      limit: 20,
      offset: targetOffset,
    );

    // Si le filtre de pharmacie de garde est actif, cibler les officines dans la requête SQLite
    if (_state.onlyOnDutyPharmacies && (searchFilter.specialty == null || searchFilter.specialty!.isEmpty)) {
      searchFilter = searchFilter.copyWith(specialty: 'pharmacie');
    }

    final searchResult = await _directoryService.search(searchFilter);

    searchResult.fold(
      onSuccess: (fetchedItems) {
        var items = fetchedItems;

        if (_state.onlyOnDutyPharmacies) {
          items = items.where((item) => item is Pharmacy && item.isOnDuty).toList();
        }

        if (_state.hasLocation) {
          items = GeoCalculator.sortByProximity(
            items,
            userLatitude: _state.userLatitude!,
            userLongitude: _state.userLongitude!,
          );
        }

        final bool reachedMax = fetchedItems.length < 20;

        if (isLoadMore) {
          final combined = [..._state.results, ...items];
          if (_state.hasLocation) {
            combined.sort((a, b) {
              final dA = a.distanceKm ?? double.infinity;
              final dB = b.distanceKm ?? double.infinity;
              return dA.compareTo(dB);
            });
          }

          _state = _state.copyWith(
            status: combined.isEmpty ? HealthSearchStatus.empty : HealthSearchStatus.success,
            results: List.unmodifiable(combined),
            hasReachedMax: reachedMax,
          );
        } else {
          _state = _state.copyWith(
            status: items.isEmpty ? HealthSearchStatus.empty : HealthSearchStatus.success,
            results: List.unmodifiable(items),
            hasReachedMax: reachedMax,
          );
        }
        notifyListeners();
      },
      onFailure: (failure) {
        _state = _state.copyWith(
          status: HealthSearchStatus.error,
          failure: failure,
        );
        notifyListeners();
      },
    );
  }

  /// Charge le lot de résultats suivant (pagination infinie)
  Future<void> loadMore() => search(isLoadMore: true);

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }
}
