import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'core/services/offline_health_search_service.dart';
import 'features/map/offline_map_view.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SanteDzMedizyApp());
}

class SanteDzMedizyApp extends StatefulWidget {
  const SanteDzMedizyApp({super.key});

  @override
  State<SanteDzMedizyApp> createState() => _SanteDzMedizyAppState();
}

class _SanteDzMedizyAppState extends State<SanteDzMedizyApp> {
  final OfflineHealthSearchService _searchService = OfflineHealthSearchService();
  bool _isReady = false;
  String _statusMessage = 'Initialisation du registre sanitaire national...';

  @override
  void initState() {
    super.initState();
    _initAppDatabase();
  }

  Future<void> _initAppDatabase() async {
    try {
      String dbPath = 'assets/data/sante_dz_bundled.db';

      // Sur Android/iOS, copier la base SQLite depuis les assets si non présente dans le stockage local
      if (Platform.isAndroid || Platform.isIOS) {
        final docDir = await getApplicationDocumentsDirectory();
        final localDb = File(p.join(docDir.path, 'sante_dz_bundled.db'));

        if (!await localDb.exists()) {
          setState(() => _statusMessage = 'Déploiement des 35 832 fiches sanitaires embarquées...');
          final data = await rootBundle.load('assets/data/sante_dz_bundled.db');
          final bytes = data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
          await localDb.writeAsBytes(bytes, flush: true);
        }
        dbPath = localDb.path;
      }

      setState(() => _statusMessage = 'Ouverture du moteur d\'indexation FTS5 et R-Tree...');
      _searchService.initialize(customPath: dbPath);

      setState(() {
        _isReady = true;
      });
    } catch (e) {
      setState(() {
        _statusMessage = 'Erreur d\'initialisation : $e';
      });
    }
  }

  @override
  void dispose() {
    _searchService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Santé DZ / Medizy',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.teal,
          primary: Colors.teal.shade800,
        ),
        useMaterial3: true,
      ),
      home: _isReady
          ? OfflineMapView(searchService: _searchService)
          : Scaffold(
              backgroundColor: Colors.teal.shade900,
              body: Center(
                child: Padding(
                  padding: const EdgeInsets.all(32.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.local_hospital,
                        size: 72,
                        color: Colors.white,
                      ),
                      const SizedBox(height: 24),
                      const Text(
                        'SANTÉ DZ / MEDIZY',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Programme National Sanitaire Algérie',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(height: 36),
                      const CircularProgressIndicator(
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                        strokeWidth: 3,
                      ),
                      const SizedBox(height: 20),
                      Text(
                        _statusMessage,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white70,
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}
