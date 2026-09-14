import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

/// Builds the app's light and dark [ThemeData].
///
/// Typography follows the spec exactly: **IBM Plex Sans** carries every
/// UI label, and **IBM Plex Mono** is reserved for technical data —
/// equipment IDs, timestamps, risk scores — never used for decoration.
/// See [monoTextStyle] / the `AppText.mono` helper for the mono cut-in.
class AppTheme {
  AppTheme._();

  static TextTheme _textTheme(Color onBackground, Color onMuted) {
    final base = GoogleFonts.ibmPlexSansTextTheme();
    return base
        .copyWith(
          displaySmall: base.displaySmall?.copyWith(fontWeight: FontWeight.w700),
          headlineSmall: base.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
          titleLarge: base.titleLarge?.copyWith(fontWeight: FontWeight.w600),
          titleMedium: base.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          bodyMedium: base.bodyMedium?.copyWith(height: 1.35),
          labelSmall: base.labelSmall?.copyWith(
            fontWeight: FontWeight.w600,
            letterSpacing: 0.6,
          ),
        )
        .apply(bodyColor: onBackground, displayColor: onBackground)
        .copyWith(
          bodySmall: base.bodySmall?.apply(color: onMuted),
        );
  }

  static ThemeData get light {
    const scheme = ColorScheme(
      brightness: Brightness.light,
      primary: AppColors.lightPrimary,
      onPrimary: AppColors.lightOnPrimary,
      secondary: AppColors.darkPrimary,
      onSecondary: Colors.white,
      error: AppColors.riskHigh,
      onError: Colors.white,
      surface: AppColors.lightSurface,
      onSurface: AppColors.lightOnBackground,
    );
    return _base(
      scheme: scheme,
      scaffoldBackground: AppColors.lightBackground,
      cardColor: AppColors.lightSurface,
      dividerColor: AppColors.lightBorder,
      textTheme: _textTheme(AppColors.lightOnBackground, AppColors.lightOnSurfaceMuted),
    );
  }

  static ThemeData get dark {
    const scheme = ColorScheme(
      brightness: Brightness.dark,
      primary: AppColors.darkPrimary,
      onPrimary: AppColors.darkOnPrimary,
      secondary: AppColors.accentOrange,
      onSecondary: Colors.black,
      error: AppColors.riskHigh,
      onError: Colors.white,
      surface: AppColors.darkSurface,
      onSurface: AppColors.darkOnBackground,
    );
    return _base(
      scheme: scheme,
      scaffoldBackground: AppColors.darkBackground,
      cardColor: AppColors.darkSurface,
      dividerColor: AppColors.darkBorder,
      textTheme: _textTheme(AppColors.darkOnBackground, AppColors.darkOnSurfaceMuted),
    );
  }

  static ThemeData _base({
    required ColorScheme scheme,
    required Color scaffoldBackground,
    required Color cardColor,
    required Color dividerColor,
    required TextTheme textTheme,
  }) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: scaffoldBackground,
      cardColor: cardColor,
      dividerColor: dividerColor,
      textTheme: textTheme,
      splashFactory: InkRipple.splashFactory,
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        foregroundColor: scheme.onSurface,
        titleTextStyle: textTheme.titleLarge,
      ),
      cardTheme: CardThemeData(
        color: cardColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: dividerColor),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: cardColor,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: dividerColor),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: dividerColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.primary, width: 1.5),
        ),
        labelStyle: textTheme.labelSmall,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          disabledBackgroundColor: dividerColor,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: textTheme.titleMedium,
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: scheme.onSurface,
          minimumSize: const Size.fromHeight(52),
          side: BorderSide(color: dividerColor),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: textTheme.titleMedium,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: scheme.primary,
          textStyle: textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
        ),
      ),
      dividerTheme: DividerThemeData(color: dividerColor, thickness: 1, space: 1),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? AppColors.accentOrange : dividerColor,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? AppColors.accentOrange.withValues(alpha: 0.35)
              : dividerColor.withValues(alpha: 0.6),
        ),
      ),
      visualDensity: VisualDensity.standard,
    );
  }

  /// The IBM Plex Mono cut-in for technical data.
  static TextStyle monoTextStyle(BuildContext context, {double? fontSize, FontWeight? fontWeight, Color? color}) {
    return GoogleFonts.ibmPlexMono(
      fontSize: fontSize ?? 13,
      fontWeight: fontWeight ?? FontWeight.w500,
      color: color ?? Theme.of(context).colorScheme.onSurface,
      letterSpacing: 0.1,
    );
  }
}
