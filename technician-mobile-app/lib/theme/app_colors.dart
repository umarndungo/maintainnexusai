import 'package:flutter/material.dart';

/// The design system's color tokens.
///
/// The dark palette is the product spec's own values (MaintainNexus —
/// Mobile & Web Experience Spec, Part 1 · Mobile · 01 "Design system") —
/// graphite surfaces with a signal-blue primary action. The light
/// palette matches the reference screenshot's warm, paper-and-ink card
/// screen: cream background, near-black primary actions.
///
/// Risk and status colors are functional, not decorative — the same
/// three colors mean the same three things everywhere in the app, in
/// both themes (per the spec's "Principles" section).
class AppColors {
  AppColors._();

  // ---------------------------------------------------------------------
  // Dark palette (spec default)
  // ---------------------------------------------------------------------
  static const darkBackground = Color(0xFF1B1F27); // Graphite 800
  static const darkSurface = Color(0xFF242835); // Graphite 700
  static const darkSurfaceRaised = Color(0xFF2C3140);
  static const darkBorder = Color(0xFF383E4E);
  static const darkOnBackground = Color(0xFFF4F2ED);
  static const darkOnSurfaceMuted = Color(0xFF9AA0AF);
  static const darkPrimary = Color(0xFF3E7CB1); // Signal blue
  static const darkOnPrimary = Color(0xFFFFFFFF);

  // ---------------------------------------------------------------------
  // Light palette (reference screenshot's card-and-paper screen)
  // ---------------------------------------------------------------------
  static const lightBackground = Color(0xFFF1ECE3);
  static const lightSurface = Color(0xFFFFFFFF);
  static const lightSurfaceRaised = Color(0xFFF7F4EE);
  static const lightBorder = Color(0xFFE3DED2);
  static const lightOnBackground = Color(0xFF17181C);
  static const lightOnSurfaceMuted = Color(0xFF6B6C72);
  static const lightPrimary = Color(0xFF17181C); // near-black pill/button
  static const lightOnPrimary = Color(0xFFFFFFFF);

  // ---------------------------------------------------------------------
  // Functional signal colors — identical in both themes
  // ---------------------------------------------------------------------
  static const riskHigh = Color(0xFFE5484D);
  static const riskMedium = Color(0xFFF2A93B);
  static const riskLow = Color(0xFF3DAA6E);
  static const accentOrange = Color(0xFFF2A93B); // floating nav active pill
  static const offlineAmber = Color(0xFFF2A93B);
  static const onlineGreen = Color(0xFF3DAA6E);

  static Color riskColor(String riskLevel) {
    switch (riskLevel.toUpperCase()) {
      case 'HIGH':
      case 'CRITICAL':
        return riskHigh;
      case 'MEDIUM':
        return riskMedium;
      default:
        return riskLow;
    }
  }
}
