import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqlite3/open.dart';
import 'package:sqlite3_flutter_libs/sqlite3_flutter_libs.dart';
import 'core/services/offline_health_search_service.dart';
import 'features/map/offline_map_view.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // sqlite3_flutter_libs configure automatiquement open.overrideFor sur Android
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
      title: 'Medizy',
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
          : MedizySplashScreen(statusMessage: _statusMessage),
    );
  }
}

/// Écran de démarrage moderne et épuré (Medizy - sans croix médicale)
class MedizySplashScreen extends StatelessWidget {
  final String statusMessage;
  const MedizySplashScreen({super.key, required this.statusMessage});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F3B36),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Conteneur circulaire doux avec symbole abstrait de bien-être / cœur connecté
              Container(
                width: 96,
                height: 96,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      Colors.teal.shade300.withOpacity(0.4),
                      Colors.teal.shade700.withOpacity(0.8),
                    ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.tealAccent.withOpacity(0.25),
                      blurRadius: 28,
                      spreadRadius: 6,
                    ),
                  ],
                  border: Border.all(
                    color: Colors.white.withOpacity(0.35),
                    width: 2,
                  ),
                ),
                child: const Center(
                  child: Icon(
                    Icons.favorite_rounded,
                    size: 46,
                    color: Colors.white,
                  ),
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                'Medizy',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Votre santé au quotidien',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 14,
                  letterSpacing: 0.3,
                ),
              ),
              const SizedBox(height: 38),
              const SizedBox(
                width: 26,
                height: 26,
                child: CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white70),
                  strokeWidth: 2.5,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                statusMessage,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white60,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
