import '../errors/database_failure.dart';
import '../models/crowd_report.dart';
import '../models/delta_patch.dart';
import '../result/result.dart';

/// Abstraction du transport réseau pour la synchronisation (découplage Offline-First)
abstract interface class ISyncTransport {
  /// Envoi sécurisé d'un lot de signalements d'anomalies vers l'API centrale
  Future<Result<bool, DatabaseFailure>> sendReportsBatch(List<CrowdReport> reports);

  /// Récupération du dernier patch différentiel selon la version locale courante
  Future<Result<DeltaPatch?, DatabaseFailure>> fetchLatestDeltaPatch(int currentDatasetVersion);
}

/// Implémentation contrôlable pour tests hermétiques et simulation réseau
class MockSyncTransport implements ISyncTransport {
  bool shouldFail = false;
  DatabaseFailure? customFailure;
  final List<List<CrowdReport>> sentBatches = [];
  DeltaPatch? nextPatch;

  @override
  Future<Result<bool, DatabaseFailure>> sendReportsBatch(List<CrowdReport> reports) async {
    if (shouldFail) {
      return Failure(
        customFailure ?? const DatabaseExecutionFailure('Échec réseau lors de l\'envoi du lot de signalements.'),
      );
    }
    sentBatches.add(List.unmodifiable(reports));
    return const Success(true);
  }

  @override
  Future<Result<DeltaPatch?, DatabaseFailure>> fetchLatestDeltaPatch(int currentDatasetVersion) async {
    if (shouldFail) {
      return Failure(
        customFailure ?? const DatabaseExecutionFailure('Échec réseau lors de la récupération du patch différentiel.'),
      );
    }
    if (nextPatch != null && nextPatch!.targetDatasetVersion > currentDatasetVersion) {
      return Success(nextPatch);
    }
    return const Success(null);
  }
}
