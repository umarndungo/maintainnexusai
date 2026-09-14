import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/home_shell_screen.dart';
import 'screens/sign_in_screen.dart';
import 'state/app_controller.dart';
import 'theme/app_theme.dart';

class MaintainNexusTechnicianApp extends StatelessWidget {
  const MaintainNexusTechnicianApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppController(),
      child: Consumer<AppController>(
        builder: (context, app, _) {
          return MaterialApp(
            title: 'MaintainNexus Technician',
            debugShowCheckedModeBanner: false,
            themeMode: app.themeMode,
            theme: AppTheme.light,
            darkTheme: AppTheme.dark,
            home: app.signedIn ? const HomeShellScreen() : const SignInScreen(),
          );
        },
      ),
    );
  }
}
