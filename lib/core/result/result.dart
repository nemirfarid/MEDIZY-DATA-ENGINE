/// Représentation générique et fonctionnelle d'un résultat d'opération
/// Garantit un typage strict et élimine les exceptions brutes non capturées.
sealed class Result<T, E> {
  const Result();

  /// Indique si l'opération a réussi
  bool get isSuccess => this is Success<T, E>;

  /// Indique si l'opération a échoué
  bool get isFailure => this is Failure<T, E>;

  /// Récupère la donnée ou null en cas d'échec
  T? get dataOrNull => switch (this) {
        Success(data: final d) => d,
        Failure() => null,
      };

  /// Récupère l'erreur ou null en cas de succès
  E? get errorOrNull => switch (this) {
        Success() => null,
        Failure(error: final e) => e,
      };

  /// Traitement exhaustif via pattern matching fonctionnel
  R fold<R>({
    required R Function(T data) onSuccess,
    required R Function(E error) onFailure,
  }) {
    return switch (this) {
      Success(data: final d) => onSuccess(d),
      Failure(error: final e) => onFailure(e),
    };
  }

  /// Transforme la donnée en cas de succès
  Result<U, E> map<U>(U Function(T data) transform) {
    return switch (this) {
      Success(data: final d) => Success(transform(d)),
      Failure(error: final e) => Failure(e),
    };
  }

  /// Transforme l'erreur en cas d'échec
  Result<T, F> mapError<F>(F Function(E error) transform) {
    return switch (this) {
      Success(data: final d) => Success(d),
      Failure(error: final e) => Failure(transform(e)),
    };
  }
}

/// Cas de succès contenant la donnée typée [data]
final class Success<T, E> extends Result<T, E> {
  final T data;

  const Success(this.data);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Success<T, E> &&
          runtimeType == other.runtimeType &&
          data == other.data;

  @override
  int get hashCode => data.hashCode;

  @override
  String toString() => 'Success<$T>($data)';
}

/// Cas d'échec contenant l'erreur typée [error]
final class Failure<T, E> extends Result<T, E> {
  final E error;

  const Failure(this.error);

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Failure<T, E> &&
          runtimeType == other.runtimeType &&
          error == other.error;

  @override
  int get hashCode => error.hashCode;

  @override
  String toString() => 'Failure<$E>($error)';
}
