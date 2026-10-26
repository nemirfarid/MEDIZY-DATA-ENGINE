import 'package:flutter/foundation.dart';
import '../../../core/errors/database_failure.dart';
import '../../../core/models/crowd_report.dart';
import '../../../core/models/health_professional.dart';
import '../../../core/result/result.dart';
import '../../../core/services/user_storage_service.dart';

/// Contrôleur d'état réactif pour la gestion des favoris, de l'historique et des signalements
class HealthFavoritesNotifier extends ChangeNotifier {
  final IUserStorageService _storageService;

  Set<int> _favoriteIds = {};
  List<HealthProfessional> _favorites = [];
  List<HealthProfessional> _recentViews = [];
  bool _isLoading = false;

  HealthFavoritesNotifier({required IUserStorageService storageService})
      : _storageService = storageService;

  Set<int> get favoriteIds => _favoriteIds;
  List<HealthProfessional> get favorites => _favorites;
  List<HealthProfessional> get recentViews => _recentViews;
  bool get isLoading => _isLoading;

  /// Vérification d'appartenance instantanée en O(1) pour l'IHM
  bool isFavorite(int facilityId) => _favoriteIds.contains(facilityId);

  /// Initialisation et hydratation du cache en mémoire
  Future<void> initialize() async {
    _isLoading = true;
    notifyListeners();

    final favResult = await _storageService.getFavorites();
    final histResult = await _storageService.getRecentViews(limit: 20);

    favResult.fold(
      onSuccess: (data) {
        _favorites = List<HealthProfessional>.from(data);
        _favoriteIds = data.map((f) => f.id).toSet();
      },
      onFailure: (_) {},
    );

    histResult.fold(
      onSuccess: (data) => _recentViews = List<HealthProfessional>.from(data),
      onFailure: (_) {},
    );

    _isLoading = false;
    notifyListeners();
  }

  /// Bascule réactive de l'état favori avec mise à jour optimiste immédiate
  Future<Result<bool, DatabaseFailure>> toggleFavorite(HealthProfessional facility) async {
    final currentlyFav = _favoriteIds.contains(facility.id);

    // 1. Mise à jour optimiste de l'état local pour fluidité IHM (0 ms de latence visuelle)
    if (currentlyFav) {
      _favoriteIds.remove(facility.id);
      _favorites = _favorites.where((f) => f.id != facility.id).toList();
    } else {
      _favoriteIds.add(facility.id);
      _favorites = [facility, ..._favorites];
    }
    notifyListeners();

    // 2. Persistance locale SQLite
    final result = await _storageService.toggleFavorite(facility);

    // Rollback en cas d'échec
    if (result.isFailure) {
      if (currentlyFav) {
        _favoriteIds.add(facility.id);
        _favorites = [facility, ..._favorites];
      } else {
        _favoriteIds.remove(facility.id);
        _favorites = _favorites.where((f) => f.id != facility.id).toList();
      }
      notifyListeners();
    }

    return result;
  }

  /// Enregistre une consultation récente dans l'historique (max 20)
  Future<void> recordView(HealthProfessional facility) async {
    // Mise à jour locale immuable
    _recentViews = [facility, ..._recentViews.where((f) => f.id != facility.id)];
    if (_recentViews.length > 20) {
      _recentViews = _recentViews.sublist(0, 20);
    }
    notifyListeners();

    await _storageService.recordView(facility);
  }

  /// Dépose un signalement collaboratif dans la file d'attente locale
  Future<Result<CrowdReport, DatabaseFailure>> submitReport(CrowdReport report) async {
    return _storageService.enqueueReport(report);
  }
}
