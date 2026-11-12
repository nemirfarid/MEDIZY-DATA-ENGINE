import 'package:flutter/material.dart';

/// Thème Medizy Premium — Féminin, Médical, Accessible
/// Palette: Teal médical (confiance), Rose/Corail (chaleur féminine), Lavande (calme)
class MedizyTheme {
  // ===== COULEURS PRINCIPALES =====
  // Teal médical — confiance, santé, professionnalisme
  static const Color primary = Color(0xFF00695C);
  static const Color primaryLight = Color(0xFF00ACC1);
  static const Color primaryDark = Color(0xFF004D40);
  static const Color primaryContainer = Color(0xFFB2DFDB);
  static const Color onPrimary = Colors.white;

  // Rose/Corail — féminité, soin, accessibilité
  static const Color accent = Color(0xFFE91E63);
  static const Color accentLight = Color(0xFFF06292);
  static const Color accentDark = Color(0xFFC2185B);
  static const Color accentContainer = Color(0xFFFCE4EC);
  static const Color onAccent = Colors.white;

  // Lavande — calme, sérénité
  static const Color secondary = Color(0xFF9C27B0);
  static const Color secondaryLight = Color(0xFFBA68C8);
  static const Color secondaryContainer = Color(0xFFE1BEE7);

  // Arrière-plans & surfaces — chaleur subtile
  static const Color background = Color(0xFFF5F9FC);  // Bleu très clair
  static const Color surface = Color(0xFFFFFFFF);     // Blanc pur
  static const Color surfaceVariant = Color(0xFFF0F4F8);
  static const Color surfaceContainer = Color(0xFFE8EEF4);

  // Texte
  static const Color textPrimary = Color(0xFF1A1A2E);      // Presque noir, lisible
  static const Color textSecondary = Color(0xFF5A6A7A);    // Gris bleuâtre
  static const Color textTertiary = Color(0xFF8A9AA8);     // Gris clair
  static const Color textOnPrimary = Colors.white;
  static const Color textOnSurface = Color(0xFF1A1A2E);

  // États
  static const Color error = Color(0xFFD32F2F);
  static const Color errorContainer = Color(0xFFFFEBEE);
  static const Color success = Color(0xFF2E7D32);
  static const Color successContainer = Color(0xFFE8F5E9);
  static const Color warning = Color(0xFFF57F17);
  static const Color warningContainer = Color(0xFFFFF8E1);
  static const Color info = Color(0xFF0288D1);
  static const Color infoContainer = Color(0xFFE1F5FE);

  // Frontières & dividers
  static const Color outline = Color(0xFFD0D8E0);
  static const Color outlineVariant = Color(0xFFE0E8F0);

  // Ombre
  static const Color shadowColor = Color(0x1A000000); // 10% noir

  // ===== ESPACEMENTS =====
  static const double spacingXs = 4.0;
  static const double spacingS = 8.0;
  static const double spacingM = 16.0;
  static const double spacingL = 24.0;
  static const double spacingXL = 32.0;
  static const double spacingXXL = 48.0;

  // ===== RAYONS DE BORDURE =====
  static const double borderRadiusXs = 4.0;
  static const double borderRadiusS = 8.0;
  static const double borderRadiusM = 16.0;
  static const double borderRadiusL = 24.0;
  static const double borderRadiusXL = 32.0;
  static const double borderRadiusFull = 9999.0;

  // ===== ZONES TACTILES =====
  static const double minTouchTarget = 48.0;
  static const double minTouchTargetLarge = 56.0;

  // ===== OMRES =====
  static const List<BoxShadow> shadowS = [
    BoxShadow(
      color: shadowColor,
      blurRadius: 4,
      offset: Offset(0, 2),
    ),
  ];

  static const List<BoxShadow> shadowM = [
    BoxShadow(
      color: shadowColor,
      blurRadius: 8,
      offset: Offset(0, 4),
    ),
    BoxShadow(
      color: Color(0x0A000000),
      blurRadius: 16,
      offset: Offset(0, 8),
    ),
  ];

  static const List<BoxShadow> shadowL = [
    BoxShadow(
      color: shadowColor,
      blurRadius: 16,
      offset: Offset(0, 8),
    ),
    BoxShadow(
      color: Color(0x0D000000),
      blurRadius: 24,
      offset: Offset(0, 12),
    ),
  ];

  // ===== THÈME LIGHT COMPLET =====
  static ThemeData get lightTheme {
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: const ColorScheme.light(
        primary: primary,
        onPrimary: onPrimary,
        primaryContainer: primaryContainer,
        onPrimaryContainer: primaryDark,
        secondary: accent,
        onSecondary: onAccent,
        secondaryContainer: accentContainer,
        onSecondaryContainer: accentDark,
        tertiary: secondary,
        onTertiary: Colors.white,
        tertiaryContainer: secondaryContainer,
        onTertiaryContainer: secondary,
        error: error,
        onError: Colors.white,
        errorContainer: errorContainer,
        onErrorContainer: error,
        surface: surface,
        onSurface: textOnSurface,
        surfaceContainerHighest: surfaceContainer,
        surfaceVariant: surfaceVariant,
        onSurfaceVariant: textSecondary,
        outline: outline,
        outlineVariant: outlineVariant,
        shadow: shadowColor,
        scrim: Color(0x80000000),
      ),
      scaffoldBackgroundColor: background,
      canvasColor: surface,
      fontFamily: 'Cairo', // Police supportant arabe + latin
      appBarTheme: AppBarTheme(
        backgroundColor: primaryDark,
        foregroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: const TextStyle(
          fontWeight: FontWeight.w800,
          fontSize: 22,
          letterSpacing: 0.5,
          color: Colors.white,
          fontFamily: 'Cairo',
        ),
        iconTheme: const IconThemeData(color: Colors.white, size: 24),
        actionsIconTheme: const IconThemeData(color: Colors.white, size: 24),
        toolbarHeight: 64,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(borderRadiusL)),
        ),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        shadowColor: shadowColor,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(borderRadiusL),
          side: BorderSide(color: outlineVariant, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: onPrimary,
          disabledBackgroundColor: outlineVariant,
          disabledForegroundColor: textTertiary,
          elevation: 0,
          shadowColor: primary.withValues(alpha: 0.3),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusM)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 15,
            letterSpacing: 0.3,
            fontFamily: 'Cairo',
          ),
          minimumSize: const Size(minTouchTargetLarge, minTouchTargetLarge),
        ).copyWith(
          overlayColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.pressed)) {
              return primaryDark.withValues(alpha: 0.1);
            }
            if (states.contains(WidgetState.hovered)) {
              return primaryLight.withValues(alpha: 0.1);
            }
            return null;
          }),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: onAccent,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusM)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 15,
            fontFamily: 'Cairo',
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: BorderSide(color: primary, width: 1.5),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusM)),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 14,
            fontFamily: 'Cairo',
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusS)),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          textStyle: const TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 14,
            fontFamily: 'Cairo',
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceVariant,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadiusM),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadiusM),
          borderSide: BorderSide(color: outlineVariant, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadiusM),
          borderSide: BorderSide(color: primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadiusM),
          borderSide: BorderSide(color: error, width: 1),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(borderRadiusM),
          borderSide: BorderSide(color: error, width: 2),
        ),
        labelStyle: TextStyle(
          color: textSecondary,
          fontSize: 14,
          fontFamily: 'Cairo',
        ),
        hintStyle: TextStyle(
          color: textTertiary,
          fontSize: 14,
          fontFamily: 'Cairo',
        ),
        floatingLabelStyle: TextStyle(
          color: primary,
          fontSize: 13,
          fontWeight: FontWeight.w600,
          fontFamily: 'Cairo',
        ),
        prefixIconColor: textTertiary,
        suffixIconColor: textTertiary,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceVariant,
        disabledColor: outlineVariant,
        selectedColor: primaryContainer,
        secondarySelectedColor: accentContainer,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        labelStyle: TextStyle(
          color: textPrimary,
          fontSize: 13,
          fontWeight: FontWeight.w500,
          fontFamily: 'Cairo',
        ),
        secondaryLabelStyle: TextStyle(
          color: onPrimary,
          fontSize: 13,
          fontWeight: FontWeight.w600,
          fontFamily: 'Cairo',
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusFull)),
        side: BorderSide(color: outlineVariant, width: 1),
        brightness: Brightness.light,
        elevation: 0,
        pressElevation: 2,
      ),
      dividerTheme: DividerThemeData(
        color: outlineVariant,
        thickness: 1,
        space: 1,
        indent: 16,
        endIndent: 16,
      ),
      listTileTheme: ListTileThemeData(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusM)),
        tileColor: Colors.transparent,
        selectedTileColor: primaryContainer,
        iconColor: textSecondary,
        textColor: textPrimary,
        titleTextStyle: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          fontFamily: 'Cairo',
        ),
        subtitleTextStyle: TextStyle(
          fontSize: 13,
          color: textSecondary,
          fontFamily: 'Cairo',
        ),
        leadingAndTrailingTextStyle: TextStyle(
          fontSize: 13,
          color: textTertiary,
          fontFamily: 'Cairo',
        ),
        minLeadingWidth: 40,
        horizontalTitleGap: 12,
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 8,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(borderRadiusXL)),
        ),
        modalBackgroundColor: surface,
        clipBehavior: Clip.antiAlias,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 16,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusXL)),
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w800,
          color: textPrimary,
          fontFamily: 'Cairo',
        ),
        contentTextStyle: TextStyle(
          fontSize: 15,
          color: textSecondary,
          height: 1.5,
          fontFamily: 'Cairo',
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: textPrimary,
        contentTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontFamily: 'Cairo',
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusM)),
        behavior: SnackBarBehavior.floating,
        elevation: 6,
        actionTextColor: accentLight,
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: primary,
        foregroundColor: onPrimary,
        elevation: 6,
        focusElevation: 8,
        hoverElevation: 8,
        highlightElevation: 10,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(borderRadiusM)),
        extendedTextStyle: TextStyle(
          fontWeight: FontWeight.w700,
          fontSize: 14,
          fontFamily: 'Cairo',
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 8,
        height: 72,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: primary,
              fontFamily: 'Cairo',
            );
          }
          return TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: textTertiary,
            fontFamily: 'Cairo',
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return IconThemeData(color: primary, size: 24);
          }
          return IconThemeData(color: textTertiary, size: 24);
        }),
        indicatorColor: primaryContainer,
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: primary,
        unselectedLabelColor: textTertiary,
        indicatorColor: primary,
        indicatorSize: TabBarIndicatorSize.label,
        labelStyle: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w700,
          fontFamily: 'Cairo',
        ),
        unselectedLabelStyle: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          fontFamily: 'Cairo',
        ),
        dividerColor: Colors.transparent,
        overlayColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.pressed)) {
            return primaryContainer;
          }
          return null;
        }),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: primary,
        inactiveTrackColor: outlineVariant,
        thumbColor: primary,
        overlayColor: primary.withValues(alpha: 0.12),
        valueIndicatorColor: primary,
        valueIndicatorTextStyle: TextStyle(
          color: onPrimary,
          fontSize: 12,
          fontFamily: 'Cairo',
        ),
        trackHeight: 4,
        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 10),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: primary,
        linearTrackColor: outlineVariant,
        circularTrackColor: outlineVariant,
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(
          fontSize: 32,
          fontWeight: FontWeight.w800,
          color: textPrimary,
          letterSpacing: -0.5,
          height: 1.2,
          fontFamily: 'Cairo',
        ),
        displayMedium: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w700,
          color: textPrimary,
          letterSpacing: -0.25,
          height: 1.25,
          fontFamily: 'Cairo',
        ),
        displaySmall: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w700,
          color: textPrimary,
          height: 1.3,
          fontFamily: 'Cairo',
        ),
        headlineLarge: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: textPrimary,
          letterSpacing: 0,
          height: 1.3,
          fontFamily: 'Cairo',
        ),
        headlineMedium: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: textPrimary,
          height: 1.35,
          fontFamily: 'Cairo',
        ),
        headlineSmall: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          height: 1.4,
          fontFamily: 'Cairo',
        ),
        titleLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: textPrimary,
          letterSpacing: 0.15,
          height: 1.4,
          fontFamily: 'Cairo',
        ),
        titleMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          letterSpacing: 0.1,
          height: 1.45,
          fontFamily: 'Cairo',
        ),
        titleSmall: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          letterSpacing: 0.1,
          height: 1.5,
          fontFamily: 'Cairo',
        ),
        bodyLarge: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w400,
          color: textPrimary,
          letterSpacing: 0.2,
          height: 1.5,
          fontFamily: 'Cairo',
        ),
        bodyMedium: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w400,
          color: textSecondary,
          letterSpacing: 0.25,
          height: 1.5,
          fontFamily: 'Cairo',
        ),
        bodySmall: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w400,
          color: textTertiary,
          letterSpacing: 0.3,
          height: 1.5,
          fontFamily: 'Cairo',
        ),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: textPrimary,
          letterSpacing: 0.1,
          height: 1.4,
          fontFamily: 'Cairo',
        ),
        labelMedium: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: textSecondary,
          letterSpacing: 0.2,
          height: 1.4,
          fontFamily: 'Cairo',
        ),
        labelSmall: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          color: textTertiary,
          letterSpacing: 0.3,
          height: 1.4,
          fontFamily: 'Cairo',
        ),
      ),
      iconTheme: const IconThemeData(
        color: textSecondary,
        size: 24,
      ),
      primaryIconTheme: const IconThemeData(
        color: Colors.white,
        size: 24,
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: textPrimary,
          borderRadius: BorderRadius.circular(borderRadiusS),
        ),
        textStyle: TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontFamily: 'Cairo',
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        preferBelow: true,
        verticalOffset: 8,
      ),
      materialTapTargetSize: MaterialTapTargetSize.padded,
      visualDensity: VisualDensity.adaptivePlatformDensity,
    );

    return base;
  }

  // ===== THÈME DARK (optionnel, pour plus tard) =====
  static ThemeData get darkTheme {
    // TODO: Implémenter thème sombre complet
    return lightTheme.copyWith(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: const Color(0xFF0F1419),
    );
  }

  // ===== HELPERS COULEURS PAR CATÉGORIE =====
  /// Retourne la couleur associée à une catégorie de santé
  static Color colorForCategory(String category) {
    final cat = category.trim().toLowerCase();
    if (cat.contains('urgenc') || cat.contains('garde') || cat.contains('samu')) {
      return error;
    }
    if (cat.contains('dentist') || cat.contains('dentaire') || cat.contains('stomatolog')) {
      return const Color(0xFF0288D1);
    }
    if (cat.contains('pédiatr') || cat.contains('pediatr') || cat.contains('enfant')) {
      return const Color(0xFF00ACC1);
    }
    if (cat.contains('pharmac') || cat.contains('officine')) {
      return success;
    }
    if (cat.contains('cardio') || cat.contains('coeur')) {
      return const Color(0xFFC62828);
    }
    if (cat.contains('laboratoire') || cat.contains('analyse') || cat.contains('biolog')) {
      return warning;
    }
    if (cat.contains('imagerie') || cat.contains('radio') || cat.contains('scanner') || cat.contains('irm')) {
      return const Color(0xFF4527A0);
    }
    if (cat.contains('ophtalmo') || cat.contains('yeux') || cat.contains('vision')) {
      return const Color(0xFF00897B);
    }
    if (cat.contains('gynéco') || cat.contains('gyneco') || cat.contains('maternit')) {
      return accent;
    }
    if (cat.contains('dermat')) {
      return const Color(0xFF8E24AA);
    }
    if (cat.contains('clinique') || cat.contains('hopital') || cat.contains('hôpital') || cat.contains('eph')) {
      return primary;
    }
    return primary; // Généraliste par défaut
  }

  /// Gradient pour les cartes de catégorie (accueil)
  static LinearGradient categoryGradient(Color baseColor) {
    return LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [
        baseColor.withValues(alpha: 0.9),
        baseColor.withValues(alpha: 0.7),
        baseColor.withValues(alpha: 0.5),
      ],
    );
  }

  /// Gradient pour le header de l'accueil
  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF00695C),
      Color(0xFF004D40),
      Color(0xFF003D34),
    ],
  );

  /// Gradient pour les boutons d'action
  static const LinearGradient actionGradient = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [
      Color(0xFF00695C),
      Color(0xFF00897B),
    ],
  );

  /// Gradient pour l'accent (féminin)
  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [
      Color(0xFFE91E63),
      Color(0xFFAD1457),
    ],
  );
}
