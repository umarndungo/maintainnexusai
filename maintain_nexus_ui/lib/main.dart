/// MaintainNexus Flutter application entry point and root app widget.
///
/// Sets up theming, app shell configuration, and launches the dashboard.
import 'package:flutter/material.dart';
import 'screens/dashboard_screen.dart'; // public: matches the DashboardScreen entry from the public code plan

/// Entry point for the MaintainNexus Flutter application.
void main() {
  runApp(const MaintainNexusApp());
}

/// Root application widget that configures app theming and startup state.
class MaintainNexusApp extends StatelessWidget {
  const MaintainNexusApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Root MaterialApp config: app title, theme, and home screen.
    return MaterialApp(
      title: 'MaintainNexus', // public: app title from the project plan
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        // App-wide color scheme and background styling.
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0F172A),
          primary: const Color(0xFF0284C7),
          secondary: const Color(0xFF38BDF8),
          background: const Color(0xFFF8FAFC),
        ),
        scaffoldBackgroundColor: const Color(0xFFF8FAFC),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0F172A),
          foregroundColor: Colors.white,
          elevation: 0,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF0284C7),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ),
      home:
          const DashboardScreen(), // public: this is the dashboard screen entry point
    );
  }
}
