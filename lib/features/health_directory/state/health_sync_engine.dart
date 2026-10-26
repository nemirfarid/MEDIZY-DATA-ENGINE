import 'package:flutter/foundation.dart';
import '../../../core/errors/database_failure.dart';
import '../../../core/models/delta_patch.dart';
import '../../../core/result/result.dart';
import '../../../core/services/delta_patch_service.dart';
import '../../../core/services/sync_transport.dart';
import '../../../core/services/user_storage_service.dart';

/// Moteur réactif d'orchestration de la synchronisation réseau et du traitement des patchs incrémentaux
class HealthSyncEngine extends ChangeNotifier {
  final IUserStorageService _storageService;
  final IDeltaPatchService _patchService;
  final ISyncTransport _transport;

  SyncStatus _status = SyncStatus.online;
  int _pendingCount = 0;
  DateTime? _lastSyncTime;
  String? _lastErrorMessage;

  HealthSyncEngine({
    required IUserStorageService storageService,
    required IDeltaPatchService patchService,
    required ISyncTransport transport,
  })  : _storageService = storageService,
        _patchService = patchService,
        _transport = transport;

  SyncStatus get status => _status;
  int get pendingCount => _pendingCount;
  DateTime? get lastSyncTime => _lastSyncTime;
  String? get lastErrorMessage => _lastErrorMessage;
  bool get isOnline => _status != SyncStatus.offline;
  bool get isSyncing => _status == SyncStatus.syncing;

  /// Initialisation et rafraîchissement des métadonnées locales
  Future<void> initialize() async {
    final pendingRes = await _storageService.getPendingReports();
    if (pendingRes.isSuccess) {
      _pendingCount = pendingRes.dataOrNull!.length;
    }

    final lastSyncRes = await _patchService.getLastSyncUtc();
    if (lastSyncRes.isSuccess) {
      _lastSyncTime = lastSyncRes.dataOrNull;
    }

    notifyListeners();
  }

  /// Mise à jour réactive du statut réseau (détecteur de connectivité)
  void setOnline(bool online) {
    if (!online) {
      _status = SyncStatus.offline;
    } else if (_status == SyncStatus.offline) {
      _status = SyncStatus.online;
    }
    notifyListeners();
  }

  /// Déclenchement de la synchronisation bidirectionnelle :
  /// 1. Dépilage et expédition du lot de signalements locaux en attente
  /// 2. Téléchargement et application du DeltaPatch incrémental
  Future<Result<bool, DatabaseFailure>> synchronize() async {
    if (_status == SyncStatus.offline) {
      return const Failure(
        DatabaseExecutionFailure('Appareil hors-ligne. Synchronisation impossible.'),
      );
    }

    if (_status == SyncStatus.syncing) {
      return const Success(false); // Synchronisation déjà en cours
    }

    _status = SyncStatus.syncing;
    _lastErrorMessage = null;
    notifyListeners();

    try {
      // 1. Dépilage des signalements non synchronisés
      final pendingResult = await _storageService.getPendingReports();
      if (pendingResult.isFailure) {
        _status = SyncStatus.error;
        _lastErrorMessage = pendingResult.errorOrNull?.message;
        notifyListeners();
        return Failure(pendingResult.errorOrNull!);
      }

      final pendingReports = pendingResult.dataOrNull!;
      if (pendingReports.isNotEmpty) {
        final sendResult = await _transport.sendReportsBatch(pendingReports);
        final reportIds = pendingReports.where((r) => r.id != null).map((r) => r.id!).toList();

        if (sendResult.isFailure) {
          // Incrémentation du compteur de retry en cas d'échec de communication
          await _storageService.incrementReportsRetryCount(reportIds);
          _status = SyncStatus.error;
          _lastErrorMessage = sendResult.errorOrNull?.message;
          notifyListeners();
          return Failure(sendResult.errorOrNull!);
        } else {
          // Validation atomique du lot expédié
          final nowUtc = DateTime.now().toUtc();
          await _storageService.markReportsAsSyncedBatch(reportIds, nowUtc);
        }
      }

      // 2. Récupération et application des éventuels DeltaPatches
      final currentVersionResult = await _patchService.getCurrentDatasetVersion();
      final currentVersion = currentVersionResult.dataOrNull ?? 1;

      final patchResult = await _transport.fetchLatestDeltaPatch(currentVersion);
      if (patchResult.isFailure) {
        _status = SyncStatus.error;
        _lastErrorMessage = patchResult.errorOrNull?.message;
        notifyListeners();
        return Failure(patchResult.errorOrNull!);
      }

      final patch = patchResult.dataOrNull;
      if (patch != null) {
        final applyResult = await _patchService.applyPatch(patch);
        if (applyResult.isFailure) {
          _status = SyncStatus.error;
          _lastErrorMessage = applyResult.errorOrNull?.message;
          notifyListeners();
          return Failure(applyResult.errorOrNull!);
        }
      }

      // 3. Mise à jour de l'état local final
      final refreshPending = await _storageService.getPendingReports();
      if (refreshPending.isSuccess) {
        _pendingCount = refreshPending.dataOrNull!.length;
      }

      final refreshLastSync = await _patchService.getLastSyncUtc();
      if (refreshLastSync.isSuccess) {
        _lastSyncTime = refreshLastSync.dataOrNull;
      }

      _status = SyncStatus.success;
      notifyListeners();
      return const Success(true);
    } catch (e, stack) {
      _status = SyncStatus.error;
      _lastErrorMessage = e.toString();
      notifyListeners();
      return Failure(DatabaseExecutionFailure('Erreur inattendue durant la synchronisation: $e', stack));
    }
  }
}
