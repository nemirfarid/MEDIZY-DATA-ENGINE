import 'package:flutter/material.dart';
import '../../../../core/models/delta_patch.dart';
import '../../state/health_sync_engine.dart';

/// Badge réactif de connectivité et de synchronisation pour l'AppBar
class SyncStatusBadge extends StatelessWidget {
  final HealthSyncEngine syncEngine;

  const SyncStatusBadge({
    super.key,
    required this.syncEngine,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: syncEngine,
      builder: (context, _) {
        final status = syncEngine.status;
        final pendingCount = syncEngine.pendingCount;

        Widget iconWidget;
        Color iconColor;
        String tooltipText;

        switch (status) {
          case SyncStatus.syncing:
            iconWidget = const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
              ),
            );
            iconColor = Colors.white;
            tooltipText = 'Synchronisation en cours...';
            break;
          case SyncStatus.offline:
            iconWidget = const Icon(Icons.cloud_off_rounded, size: 20);
            iconColor = Colors.white60;
            tooltipText = 'Mode hors-ligne';
            break;
          case SyncStatus.error:
            iconWidget = const Icon(Icons.sync_problem_rounded, size: 20);
            iconColor = Colors.orangeAccent;
            tooltipText = syncEngine.lastErrorMessage != null
                ? 'Erreur: ${syncEngine.lastErrorMessage}'
                : 'Erreur de synchronisation. Appuyez pour réessayer.';
            break;
          case SyncStatus.success:
          case SyncStatus.online:
            iconWidget = const Icon(Icons.cloud_done_rounded, size: 20);
            iconColor = Colors.white;
            tooltipText = pendingCount > 0
                ? '$pendingCount signalement(s) en attente. Appuyez pour synchroniser.'
                : 'Données synchronisées';
            break;
        }

        final content = pendingCount > 0 && status != SyncStatus.syncing
            ? Badge(
                label: Text(
                  '$pendingCount',
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                backgroundColor: status == SyncStatus.error ? Colors.deepOrange : Colors.amber.shade800,
                child: IconTheme(
                  data: IconThemeData(color: iconColor),
                  child: iconWidget,
                ),
              )
            : IconTheme(
                data: IconThemeData(color: iconColor),
                child: iconWidget,
              );

        return IconButton(
          tooltip: tooltipText,
          icon: content,
          onPressed: () async {
            if (syncEngine.isSyncing) return;
            final res = await syncEngine.synchronize();
            if (context.mounted) {
              if (res.isFailure) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(res.errorOrNull?.message ?? 'Échec de synchronisation'),
                    backgroundColor: Colors.red.shade700,
                    duration: const Duration(seconds: 3),
                  ),
                );
              } else if (res.dataOrNull == true) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Synchronisation réussie !'),
                    backgroundColor: Colors.teal,
                    duration: const Duration(seconds: 2),
                  ),
                );
              }
            }
          },
        );
      },
    );
  }
}
