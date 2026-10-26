/// Hiérarchie d'erreurs typées pour les opérations de base de données SQLite
sealed class DatabaseFailure {
  final String message;
  final Object? cause;

  const DatabaseFailure(this.message, [this.cause]);

  @override
  String toString() {
    if (cause != null) {
      return '$runtimeType: $message (Cause: $cause)';
    }
    return '$runtimeType: $message';
  }
}

/// Fichier de base de données SQLite introuvable sur le disque ou dans les assets
final class DatabaseNotFoundFailure extends DatabaseFailure {
  const DatabaseNotFoundFailure(super.message, [super.cause]);
}

/// Échec lors de la préparation ou de l'exécution d'une requête SQL
final class DatabaseExecutionFailure extends DatabaseFailure {
  const DatabaseExecutionFailure(super.message, [super.cause]);
}

/// Tentative d'accès alors que la base SQLite n'est pas initialisée ou a été fermée
final class DatabaseClosedFailure extends DatabaseFailure {
  const DatabaseClosedFailure(super.message, [super.cause]);
}

/// Erreur de validation des critères ou paramètres de recherche
final class DatabaseValidationFailure extends DatabaseFailure {
  const DatabaseValidationFailure(super.message, [super.cause]);
}
