// MaintainNexus Flutter application entry point and root app widget.
//
// Sets up theming, app shell configuration, and launches the dashboard.
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
        // App-wide color scheme inspired by the icon palette.
        colorScheme: const ColorScheme(
          brightness: Brightness.light,
          primary: Color(0xFFC8102E),
          onPrimary: Colors.white,
          secondary: Color(0xFF111111),
          onSecondary: Colors.white,
          error: Color(0xFFB00020),
          onError: Colors.white,
          background: Color(0xFFF7F7F7),
          onBackground: Colors.black,
          surface: Colors.white,
          onSurface: Colors.black,
        ),
        scaffoldBackgroundColor: const Color(0xFFF7F7F7),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF111111),
          foregroundColor: Colors.white,
          elevation: 0,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFFC8102E),
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
