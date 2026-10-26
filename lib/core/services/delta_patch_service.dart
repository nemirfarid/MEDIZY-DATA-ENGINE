import '../errors/database_failure.dart';
import '../models/delta_patch.dart';
import '../models/health_professional.dart';
import '../result/result.dart';
import 'user_storage_service.dart';

/// Contrat pour le service de gestion des patchs incrémentaux et du versionnage local
abstract interface class IDeltaPatchService {
  Future<Result<int, DatabaseFailure>> getCurrentDatasetVersion();
  Future<Result<void, DatabaseFailure>> applyPatch(DeltaPatch patch);
  Future<Result<DateTime?, DatabaseFailure>> getLastSyncUtc();
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getPatchedFacilities();
}

/// Service métier d'application des mises à jour incrémentales (DeltaPatches) sans re-téléchargement global
class HealthDeltaPatchService implements IDeltaPatchService {
  final IUserStorageService _storageService;

  static const String _keyDatasetVersion = 'dataset_version';
  static const String _keyLastSyncUtc = 'last_sync_utc';

  HealthDeltaPatchService({required IUserStorageService storageService})
      : _storageService = storageService;

  @override
  Future<Result<int, DatabaseFailure>> getCurrentDatasetVersion() async {
    final metaResult = await _storageService.getMetadata(_keyDatasetVersion);
    if (metaResult.isFailure) return Failure(metaResult.errorOrNull!);

    final val = metaResult.dataOrNull;
    if (val == null || val.trim().isEmpty) {
      return const Success(1); // Version initiale bundled
    }

    final parsed = int.tryParse(val) ?? 1;
    return Success(parsed);
  }

  @override
  Future<Result<void, DatabaseFailure>> applyPatch(DeltaPatch patch) async {
    // 1. Application atomique dans la table de surcouche facility_patches
    final patchResult = await _storageService.applyFacilityPatch(
      patchId: patch.patchId,
      version: patch.targetDatasetVersion,
      upserts: patch.upserts,
      deletions: patch.deletions,
    );

    if (patchResult.isFailure) {
      return patchResult;
    }

    // 2. Mise à jour des métadonnées locales (version du dataset et horodatage UTC)
    final versionResult = await _storageService.setMetadata(
      _keyDatasetVersion,
      patch.targetDatasetVersion.toString(),
    );
    if (versionResult.isFailure) return versionResult;

    final syncResult = await _storageService.setMetadata(
      _keyLastSyncUtc,
      patch.issuedAt.toUtc().toIso8601String(),
    );
    if (syncResult.isFailure) return syncResult;

    return const Success(null);
  }

  @override
  Future<Result<DateTime?, DatabaseFailure>> getLastSyncUtc() async {
    final metaResult = await _storageService.getMetadata(_keyLastSyncUtc);
    if (metaResult.isFailure) return Failure(metaResult.errorOrNull!);

    final val = metaResult.dataOrNull;
    if (val == null || val.trim().isEmpty) {
      return const Success(null);
    }

    final dt = DateTime.tryParse(val);
    return Success(dt);
  }

  @override
  Future<Result<List<HealthProfessional>, DatabaseFailure>> getPatchedFacilities() async {
    return _storageService.getPatchedFacilities();
  }
}
