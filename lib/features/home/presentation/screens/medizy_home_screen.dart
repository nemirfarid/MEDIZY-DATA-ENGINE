import '../../../emergency/presentation/widgets/sos_emergency_sheet.dart';
import '../../../../core/services/medizy_locale.dart';
import '../../../pharma/presentation/widgets/solidarity_sheet.dart';
import 'package:flutter/material.dart';
import '../../../../core/models/health_search_filter.dart';
import '../../../../core/services/offline_health_search_service.dart';
import '../../../../core/theme/medizy_theme.dart';
import '../../../health_directory/presentation/screens/health_search_screen.dart';
import '../../../health_directory/services/health_directory_service.dart';
import '../../../health_directory/state/health_search_notifier.dart';
import '../../../map/offline_map_view.dart';
import '../../../pharma/presentation/widgets/dci_equivalents_sheet.dart';
import '../../../pharma/services/dz_medication_service.dart';
import '../widgets/category_grid.dart';

/// Page d'accueil Medizy Premium — Design médical, féminin, bilingue FR/AR
class MedizyHomeScreen extends StatefulWidget {
  final OfflineHealthSearchService searchService;
  final HealthSearchNotifier? notifier;
  final DzMedicationService? medicationService;

  const MedizyHomeScreen({
    super.key,
    required this.searchService,
    this.notifier,
    this.medicationService,
  });

  @override
  State<MedizyHomeScreen> createState() => _MedizyHomeScreenState();
}

class _MedizyHomeScreenState extends State<MedizyHomeScreen>
    with SingleTickerProviderStateMixin {
  late final HealthSearchNotifier _notifier;
  late final DzMedicationService _medicationService;
  late final AnimationController _heroController;
  late final Animation<double> _heroFadeAnimation;
  late final Animation<Offset> _heroSlideAnimation;

  @override
  void initState() {
    super.initState();
    _notifier = widget.notifier ??
        HealthSearchNotifier(
          directoryService: HealthDirectoryService(),
        );
    _medicationService = widget.medicationService ?? DzMedicationService();
    if (!_medicationService.isInitialized) {
      _medicationService.initialize();
    }

    _heroController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );

    _heroFadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _heroController, curve: const Interval(0.0, 0.6, curve: Curves.easeOut)),
    );

    _heroSlideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _heroController, curve: const Interval(0.2, 0.8, curve: Curves.easeOutCubic)),
    );

    _heroController.forward();
  }

  @override
  void dispose() {
    _heroController.dispose();
    super.dispose();
  }

  void _onCategorySelected(String slug) {
    _notifier.setFilter(HealthSearchFilter(category: slug));
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => OfflineMapView(
          searchService: widget.searchService,
          initialCategory: slug,
        ),
      ),
    );
  }

  void _toggleLanguage() {
    setState(() {
      MedizyLocale.toggleLanguage();
    });
  }

  void _navigateToMap() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => OfflineMapView(searchService: widget.searchService),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isArabic = MedizyLocale.isArabic;

    return Directionality(
      textDirection: isArabic ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: MedizyTheme.background,
        appBar: AppBar(
          elevation: 0,
          backgroundColor: MedizyTheme.primaryDark,
          foregroundColor: Colors.white,
          surfaceTintColor: Colors.transparent,
          toolbarHeight: 72,
          title: AnimatedBuilder(
            animation: _heroController,
            builder: (context, child) {
              return FadeTransition(
                opacity: _heroFadeAnimation,
                child: SlideTransition(
                  position: _heroSlideAnimation,
                  child: Row(
                    children: [
                      // Logo Medizy animé
                      Hero(
                        tag: 'medizy_logo',
                        child: Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                            color: Colors.white,
                            boxShadow: [
                              BoxShadow(
                                color: MedizyTheme.primary.withValues(alpha: 0.2),
                                blurRadius: 8,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusS),
                            child: Image.asset(
                              'assets/images/medizy_logo.png',
                              width: 40,
                              height: 40,
                              fit: BoxFit.cover,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 14),
                      // Titre avec gradient
                      ShaderMask(
                        shaderCallback: (bounds) => const LinearGradient(
                          colors: [Colors.white, Color(0xFFB2DFDB)],
                        ).createShader(bounds),
                        child: Text(
                          'MEDIZY',
                          style: TextStyle(
                            fontWeight: FontWeight.w900,
                            fontSize: 24,
                            letterSpacing: 1.5,
                            color: Colors.white,
                            fontFamily: 'Cairo',
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
          actions: [
            // Solidarité
            IconButton(
              icon: const Icon(Icons.volunteer_activism_rounded, size: 26),
              tooltip: MedizyLocale.t('Solidarité', 'تضامن'),
              onPressed: () => SolidaritySheet.show(context),
            ),
            // Équivalents DCI
            IconButton(
              icon: const Icon(Icons.medication_rounded, size: 26),
              tooltip: MedizyLocale.t('Équivalents DCI', 'مكافئات DCI'),
              onPressed: () => DciEquivalentsSheet.show(context, medicationService: _medicationService),
            ),
            // Recherche globale
            IconButton(
              icon: const Icon(Icons.search_rounded, size: 26),
              tooltip: MedizyLocale.t('Rechercher', 'بحث'),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => HealthSearchScreen(notifier: _notifier)),
              ),
            ),
            // Bascule langue FR/AR
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Material(
                color: Colors.white.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                child: InkWell(
                  onTap: _toggleLanguage,
                  borderRadius: BorderRadius.circular(12),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          isArabic ? Icons.translate_rounded : Icons.language_rounded,
                          color: MedizyTheme.accentLight,
                          size: 20,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          isArabic ? 'FR' : 'العربية',
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                            color: Colors.white,
                            fontFamily: 'Cairo',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
        body: SafeArea(
          child: AnimatedBuilder(
            animation: _heroController,
            builder: (context, child) {
              return FadeTransition(
                opacity: _heroFadeAnimation,
                child: SlideTransition(
                  position: _heroSlideAnimation,
                  child: Column(
                    children: [
                      // ===== HERO SECTION =====
                      Container(
                        width: double.infinity,
                        padding: EdgeInsets.fromLTRB(
                          MedizyTheme.spacingM,
                          MedizyTheme.spacingM,
                          MedizyTheme.spacingM,
                          MedizyTheme.spacingL,
                        ),
                        decoration: const BoxDecoration(
                          gradient: MedizyTheme.heroGradient,
                          borderRadius: BorderRadius.vertical(bottom: Radius.circular(MedizyTheme.borderRadiusXL + 8)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Titre principal
                            Text(
                              MedizyLocale.t('Annuaire Sanitaire National', 'الدليل الصحي الوطني'),
                              style: const TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.w900,
                                color: Colors.white,
                                letterSpacing: 0.3,
                                fontFamily: 'Cairo',
                              ),
                            ),
                            const SizedBox(height: MedizyTheme.spacingXs),
                            // Sous-titre
                            Text(
                              MedizyLocale.t('40 752 structures • 1 541 communes • 58 wilayas', '40 752 هيكل • 1 541 بلدية • 58 ولاية'),
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w500,
                                color: Colors.white.withValues(alpha: 0.9),
                                fontFamily: 'Cairo',
                              ),
                            ),
                            const SizedBox(height: MedizyTheme.spacingM),
                            // Instruction
                            Text(
                              MedizyLocale.t('Sélectionnez une spécialité pour consulter la carte', 'اختر تخصصاً لاستعراض الخريطة'),
                              style: TextStyle(
                                fontSize: 13,
                                color: Colors.white.withValues(alpha: 0.8),
                                fontFamily: 'Cairo',
                              ),
                            ),
                            const SizedBox(height: MedizyTheme.spacingL),
                            // Bouton SOS Premium
                            SizedBox(
                              width: double.infinity,
                              height: 56,
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.emergency_rounded, color: Colors.white, size: 26),
                                label: Text(
                                  MedizyLocale.t('SOS Urgences 24/7', 'طوارئ صحية 24/7'),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w800,
                                    fontSize: 16,
                                    letterSpacing: 0.3,
                                    fontFamily: 'Cairo',
                                  ),
                                ),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: MedizyTheme.error,
                                  foregroundColor: Colors.white,
                                  elevation: 0,
                                  shadowColor: MedizyTheme.error.withValues(alpha: 0.4),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                                  ),
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                ).copyWith(
                                  overlayColor: WidgetStateProperty.resolveWith((states) {
                                    if (states.contains(WidgetState.pressed)) {
                                      return MedizyTheme.error.withValues(alpha: 0.2);
                                    }
                                    return null;
                                  }),
                                ),
                                onPressed: () => SosEmergencySheet.show(context, searchService: widget.searchService),
                              ),
                            ),
                          ],
                        ),
                      ),

                      // ===== CATÉGORIES GRID =====
                      Expanded(
                        child: SingleChildScrollView(
                          physics: const BouncingScrollPhysics(),
                          padding: EdgeInsets.only(
                            top: MedizyTheme.spacingM,
                            bottom: MedizyTheme.spacingM,
                            left: MedizyTheme.spacingM,
                            right: MedizyTheme.spacingM,
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Section titre
                              Padding(
                                padding: EdgeInsets.only(
                                  left: MedizyTheme.spacingS,
                                  bottom: MedizyTheme.spacingS,
                                ),
                                child: Row(
                                  children: [
                                    Container(
                                      width: 4,
                                      height: 22,
                                      decoration: BoxDecoration(
                                        color: MedizyTheme.accent,
                                        borderRadius: BorderRadius.circular(2),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Text(
                                      MedizyLocale.t('Spécialités médicales', 'التخصصات الطبية'),
                                      style: const TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.w800,
                                        color: MedizyTheme.textPrimary,
                                        fontFamily: 'Cairo',
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              // Grille des catégories
                              CategoryGrid(
                                searchService: widget.searchService,
                                onCategorySelected: _onCategorySelected,
                              ),
                            ],
                          ),
                        ),
                      ),

                      // ===== BARRE D'ACTION INFÉRIEURE =====
                      Container(
                        padding: EdgeInsets.all(MedizyTheme.spacingM),
                        decoration: BoxDecoration(
                          color: MedizyTheme.surface,
                          borderRadius: BorderRadius.vertical(top: Radius.circular(MedizyTheme.borderRadiusXL)),
                          boxShadow: MedizyTheme.shadowM,
                          border: Border(
                            top: BorderSide(color: MedizyTheme.outlineVariant, width: 1),
                          ),
                        ),
                        child: SafeArea(
                          top: false,
                          child: Row(
                            children: [
                              Expanded(
                                child: SizedBox(
                                  height: 54,
                                  child: ElevatedButton.icon(
                                    icon: const Icon(Icons.my_location_rounded, size: 22),
                                    label: Text(
                                      MedizyLocale.t('Près de moi', 'بالقرب مني'),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w800,
                                        fontSize: 15,
                                        fontFamily: 'Cairo',
                                      ),
                                    ),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: MedizyTheme.primary,
                                      foregroundColor: Colors.white,
                                      elevation: 0,
                                      shadowColor: MedizyTheme.primary.withValues(alpha: 0.3),
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(MedizyTheme.borderRadiusM),
                                      ),
                                    ).copyWith(
                                      overlayColor: WidgetStateProperty.resolveWith((states) {
                                        if (states.contains(WidgetState.pressed)) {
                                          return MedizyTheme.primaryDark.withValues(alpha: 0.15);
                                        }
                                        return null;
                                      }),
                                    ),
                                    onPressed: _navigateToMap,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}