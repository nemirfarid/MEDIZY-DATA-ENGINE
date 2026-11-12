import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'core/services/medizy_locale.dart';
import 'core/services/offline_health_search_service.dart';
import 'core/theme/medizy_theme.dart';
import 'features/home/presentation/screens/medizy_home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Initialiser la locale (par défaut FR)
  MedizyLocale.isArabic = false;
  runApp(const SanteDzMedizyApp());
}

class SanteDzMedizyApp extends StatefulWidget {
  const SanteDzMedizyApp({super.key});

  @override
  State<SanteDzMedizyApp> createState() => _SanteDzMedizyAppState();
}

class _SanteDzMedizyAppState extends State<SanteDzMedizyApp> {
  final OfflineHealthSearchService _searchService = OfflineHealthSearchService();
  // Version de la base de données bundlée - incrémenter lors de changements de schéma/données
  static const int _bundledDbVersion = 33;
  bool _isReady = false;
  String _statusMessage = MedizyLocale.t('Initialisation du registre sanitaire national...', 'جاري تهيئة السجل الصحي الوطني...');

  @override
  void initState() {
    super.initState();
    _initAppDatabase();
  }

  Future<void> _initAppDatabase() async {
    try {
      String dbPath = 'assets/data/sante_dz_bundled.db';

      // Sur Android/iOS, copier la base SQLite depuis les assets si non présente ou si mise à jour
      if (Platform.isAndroid || Platform.isIOS) {
        final docDir = await getApplicationDocumentsDirectory();
        final localDb = File(p.join(docDir.path, 'sante_dz_bundled.db'));
        final versionFile = File(p.join(docDir.path, 'sante_dz_bundled.version'));
        final assetData = await rootBundle.load('assets/data/sante_dz_bundled.db');
        final assetLength = assetData.lengthInBytes;

        bool needsCopy = !await localDb.exists();
        if (!needsCopy) {
          final localLength = await localDb.length();
          final hasVersion = await versionFile.exists();
          if (!hasVersion) {
            // Anciennes versions n'enregistraient pas la version DB. Rafraîchir une fois.
            needsCopy = true;
          } else {
            final localVersion = int.tryParse((await versionFile.readAsString()).trim()) ?? 0;
            needsCopy = localVersion != _bundledDbVersion || localLength != assetLength;
          }
        }
        if (needsCopy) {
          setState(() => _statusMessage = MedizyLocale.t('Déploiement des 40 752 structures sanitaires...', 'نشر 40 752 هيكل صحي...'));
          final bytes = assetData.buffer.asUint8List(assetData.offsetInBytes, assetData.lengthInBytes);
          final temporaryDb = File('${localDb.path}.new');
          await temporaryDb.writeAsBytes(bytes, flush: true);
          for (final suffix in ['-wal', '-shm']) {
            final sidecar = File('${localDb.path}$suffix');
            if (await sidecar.exists()) await sidecar.delete();
          }
          if (await localDb.exists()) await localDb.delete();
          await temporaryDb.rename(localDb.path);
          await versionFile.writeAsString('$_bundledDbVersion', flush: true);
        }
        dbPath = localDb.path;
      }

      setState(() => _statusMessage = MedizyLocale.t('Ouverture du moteur d\'indexation FTS5 et R-Tree...', 'فتح محرك الفهرسة FTS5 و R-Tree...'));
      _searchService.initialize(customPath: dbPath);

      setState(() {
        _isReady = true;
      });
    } catch (e) {
      setState(() {
        _statusMessage = '${MedizyLocale.t('Erreur d\'initialisation', 'خطأ في التهيئة')} : $e';
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
      theme: MedizyTheme.lightTheme,
      darkTheme: MedizyTheme.darkTheme,
      themeMode: ThemeMode.light,
      home: _isReady
          ? MedizyHomeScreen(searchService: _searchService)
          : MedizySplashScreen(statusMessage: _statusMessage),
    );
  }
}

/// Écran de démarrage Medizy Premium — Design médical, féminin, bilingue
class MedizySplashScreen extends StatelessWidget {
  final String statusMessage;
  const MedizySplashScreen({super.key, required this.statusMessage});

  @override
  Widget build(BuildContext context) {
    final isArabic = MedizyLocale.isArabic;

    return Directionality(
      textDirection: isArabic ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: MedizyTheme.primaryDark,
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo Medizy avec animation
                TweenAnimationBuilder<double>(
                  duration: const Duration(milliseconds: 1200),
                  tween: Tween(begin: 0.0, end: 1.0),
                  curve: Curves.elasticOut,
                  builder: (context, value, child) {
                    return Transform.scale(
                      scale: value,
                      child: Opacity(opacity: value, child: child),
                    );
                  },
                  child: Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(28),
                      boxShadow: [
                        BoxShadow(
                          color: MedizyTheme.primaryLight.withValues(alpha: 0.4),
                          blurRadius: 40,
                          spreadRadius: 8,
                        ),
                        BoxShadow(
                          color: MedizyTheme.accent.withValues(alpha: 0.2),
                          blurRadius: 20,
                          spreadRadius: 4,
                        ),
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(28),
                      child: Image.asset(
                        'assets/images/medizy_logo.png',
                        width: 120,
                        height: 120,
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                // Titre
                ShaderMask(
                  shaderCallback: (bounds) => const LinearGradient(
                    colors: [Colors.white, Color(0xFFB2DFDB)],
                  ).createShader(bounds),
                  child: Text(
                    'MEDIZY',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 36,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 2.0,
                      fontFamily: 'Cairo',
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                // Slogan
                Text(
                  MedizyLocale.t('Votre santé au quotidien', 'صحتك في متناول يدك'),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.85),
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.5,
                    fontFamily: 'Cairo',
                  ),
                ),
                const SizedBox(height: 48),
                // Indicateur de chargement stylisé
                SizedBox(
                  width: 32,
                  height: 32,
                  child: CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation<Color>(MedizyTheme.accentLight),
                    strokeWidth: 3,
                    backgroundColor: Colors.white.withValues(alpha: 0.1),
                  ),
                ),
                const SizedBox(height: 24),
                // Message de statut
                Text(
                  statusMessage,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.7),
                    fontSize: 13,
                    fontFamily: 'Cairo',
                    height: 1.4,
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