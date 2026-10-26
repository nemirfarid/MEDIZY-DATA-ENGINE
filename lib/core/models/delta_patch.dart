import 'package:meta/meta.dart';
import 'health_professional.dart';
import 'pharmacy.dart';

/// Statut de connectivité et de synchronisation du moteur réseau
enum SyncStatus {
  offline('Hors-ligne'),
  online('Connecté'),
  syncing('Synchronisation en cours...'),
  success('Synchronisé avec succès'),
  error('Erreur de synchronisation');

  final String label;
  const SyncStatus(this.label);
}

/// Métadonnées d'audit et de versionnage des données locales
@immutable
class SyncMetadata {
  final int schemaVersion;
  final int datasetVersion;
  final DateTime? lastSyncUtc;
  final int pendingReportsCount;

  const SyncMetadata({
    this.schemaVersion = 1,
    this.datasetVersion = 1,
    this.lastSyncUtc,
    this.pendingReportsCount = 0,
  });

  SyncMetadata copyWith({
    int? schemaVersion,
    int? datasetVersion,
    DateTime? lastSyncUtc,
    int? pendingReportsCount,
  }) {
    return SyncMetadata(
      schemaVersion: schemaVersion ?? this.schemaVersion,
      datasetVersion: datasetVersion ?? this.datasetVersion,
      lastSyncUtc: lastSyncUtc ?? this.lastSyncUtc,
      pendingReportsCount: pendingReportsCount ?? this.pendingReportsCount,
    );
  }

  @override
  String toString() =>
      'SyncMetadata(datasetV: $datasetVersion, lastSync: $lastSyncUtc, pending: $pendingReportsCount)';
}

/// Modèle immuable d'un patch différentiel incrémental pour mise à jour sans re-téléchargement global
@immutable
class DeltaPatch {
  final String patchId;
  final int targetDatasetVersion;
  final DateTime issuedAt;
  final List<HealthProfessional> upserts;
  final List<int> deletions;

  const DeltaPatch({
    required this.patchId,
    required this.targetDatasetVersion,
    required this.issuedAt,
    this.upserts = const [],
    this.deletions = const [],
  });

  factory DeltaPatch.fromJson(Map<String, dynamic> json) {
    final upsertsList = <HealthProfessional>[];
    if (json['upserts'] is List) {
      for (final item in json['upserts'] as List) {
        if (item is Map<String, dynamic>) {
          final cat = (item['categorie'] as String?)?.toLowerCase() ?? '';
          if (cat.contains('pharmacie')) {
            upsertsList.add(Pharmacy.fromRow(item));
          } else {
            upsertsList.add(HealthProfessional.fromRow(item));
          }
        }
      }
    }

    final deletionsList = <int>[];
    if (json['deletions'] is List) {
      for (final id in json['deletions'] as List) {
        if (id is num) deletionsList.add(id.toInt());
      }
    }

    return DeltaPatch(
      patchId: (json['patch_id'] as String?) ?? 'patch-unknown',
      targetDatasetVersion: (json['target_dataset_version'] as num?)?.toInt() ?? 1,
      issuedAt: DateTime.tryParse(json['issued_at']?.toString() ?? '') ?? DateTime.now().toUtc(),
      upserts: List.unmodifiable(upsertsList),
      deletions: List.unmodifiable(deletionsList),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'patch_id': patchId,
      'target_dataset_version': targetDatasetVersion,
      'issued_at': issuedAt.toIso8601String(),
      'upserts': upserts.map((u) => u.toMap()).toList(),
      'deletions': deletions,
    };
  }

  @override
  String toString() =>
      'DeltaPatch(id: $patchId, v: $targetDatasetVersion, upserts: ${upserts.length}, deletions: ${deletions.length})';
}
