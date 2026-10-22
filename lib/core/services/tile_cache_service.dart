import 'dart:io';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

/// Service de cache disque des tuiles OpenStreetMap.
///
/// Les tuiles sont stockées dans le répertoire documents de l'application
/// sous la forme : `tiles/{z}/{x}/{y}.png`
///
/// Aucune expiration prématurée n'est appliquée : une tuile mise en cache
/// reste disponible indéfiniment pour une utilisation hors-ligne totale.
class TileCacheService {
  static final TileCacheService _instance = TileCacheService._internal();
  factory TileCacheService() => _instance;

  Directory? _cacheDir;
  final _cacheMap = <String, Uint8List>{}; // cache mémoire "clé z/x/y"
  final bool _isWeb = kIsWeb;

  TileCacheService._internal();

  /// Initialise le répertoire de cache disque.
  Future<void> init() async {
    if (_isWeb) return;
    final docsDir = await getApplicationDocumentsDirectory();
    _cacheDir = Directory('${docsDir.path}/tiles');
    await _cacheDir?.create(recursive: true);
  }

  Directory? get cacheDir => _cacheDir;

  /// Génère la clé de cache pour une tuile.
  String _tileKey(int z, int x, int y) => '$z/$x/$y';

  /// Chemin fichier d'une tuile sur disque.
  String _tilePath(int z, int x, int y) {
    if (_cacheDir == null) return '';
    final dir = Directory('${_cacheDir!.path}/$z/$x');
    dir.createSync(recursive: true);
    return '${dir.path}/$y.png';
  }

  /// Vérifie si une tuile est présente sur disque.
  bool hasTile(int z, int x, int y) {
    final key = _tileKey(z, x, y);
    if (_cacheMap.containsKey(key)) return true;
    if (_cacheDir == null) return false;
    return File(_tilePath(z, x, y)).existsSync();
  }

  /// Récupère une tuile depuis le cache disque ou mémoire.
  Uint8List? getTileFromCache(int z, int x, int y) {
    final key = _tileKey(z, x, y);
    if (_cacheMap.containsKey(key)) return _cacheMap[key];
    if (_cacheDir == null) return null;
    final path = _tilePath(z, x, y);
    if (File(path).existsSync()) {
      final bytes = File(path).readAsBytesSync();
      _cacheMap[key] = bytes;
      return bytes;
    }
    return null;
  }

  /// Stocke une tuile dans le cache disque et mémoire.
  Future<void> storeTile(int z, int x, int y, Uint8List bytes) async {
    final key = _tileKey(z, x, y);
    _cacheMap[key] = bytes;
    if (_cacheDir == null) return;
    final path = _tilePath(z, x, y);
    await File(path).writeAsBytes(bytes, flush: true);
  }

  /// Télécharge une tuile depuis le réseau et la met en cache disque.
  /// Retourne les octets ou null en cas d'échec.
  Future<Uint8List?> downloadTile(String urlTemplate, int z, int x, int y) async {
    if (_isWeb) return null;

    // Remplace les placeholders de l'URL
    final url = urlTemplate
        .replaceAll('{z}', z.toString())
        .replaceAll('{x}', x.toString())
        .replaceAll('{y}', y.toString());

    try {
      final uri = Uri.parse(url);
      final client = HttpClient()
        ..connectionTimeout = const Duration(seconds: 8)
        ..idleTimeout = const Duration(seconds: 8);

      final request = await client.openUrl('GET', uri);
      request.headers.add('User-Agent', 'Medizy-Algeria/1.0.19 (dz.sante.medizy.national)');
      final response = await request.close();

      if (response.statusCode == 200) {
        final bytes = await consolidateHttpClientResponseBytes(response);
        await storeTile(z, x, y, bytes);
        return bytes;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  /// Nombre de tuiles actuellement en cache disque.
  int get cachedTileCount => _cacheMap.length;

  /// Efface tout le cache disque (utilisé pour réinitialisation).
  Future<void> clearCache() async {
    _cacheMap.clear();
    if (_cacheDir != null && await _cacheDir!.exists()) {
      await _cacheDir!.delete(recursive: true);
      await _cacheDir!.create(recursive: true);
    }
  }
}

/// Prépare le cache de tuiles au démarrage de l'application.
Future<void> initTileCache() async {
  await TileCacheService().init();
}

/// Télécharge en arrière-plan les tuiles d'une zone donnée (pré-téléchargement wilaya).
/// Retourne le nombre de tuiles mises en cache.
Future<int> preloadTilesForBounds({
  required double minLat,
  required double maxLat,
  required double minLon,
  required double maxLon,
  required int minZoom,
  required int maxZoom,
  required String urlTemplate,
}) async {
  final cache = TileCacheService();
  var count = 0;

  for (var z = minZoom; z <= maxZoom; z++) {
    // Calculer la plage de tuiles pour ce niveau de zoom
    final xMin = _lonToTileX(minLon, z);
    final xMax = _lonToTileX(maxLon, z);
    final yMin = _latToTileY(maxLat, z); // note : y inversé (nord = petite y)
    final yMax = _latToTileY(minLat, z);

    for (var x = xMin; x <= xMax; x++) {
      for (var y = yMin; y <= yMax; y++) {
        if (cache.hasTile(z, x, y)) continue;
        final bytes = await cache.downloadTile(urlTemplate, z, x, y);
        if (bytes != null) count++;
        // Petit délai pour ne pas saturer le réseau
        await Future.delayed(const Duration(milliseconds: 20));
      }
    }
  }

  return count;
}

/// Convertit une longitude en coordonnée de tuile X.
int _lonToTileX(double lon, int z) {
  return ((lon + 180) / 360 * (1 << z)).floor();
}

/// Convertit une latitude en coordonnée de tuile Y.
int _latToTileY(double lat, int z) {
  final latRad = lat * pi / 180;
  return ((1 - (log((1 + sin(latRad)) / cos(latRad)) / pi)) / 2 * (1 << z)).floor();
}
