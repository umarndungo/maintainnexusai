import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/home_shell_screen.dart';
import 'screens/sign_in_screen.dart';
import 'services/deep_link_service.dart';
import 'state/app_controller.dart';
import 'theme/app_theme.dart';

class MaintainNexusTechnicianApp extends StatelessWidget {
  const MaintainNexusTechnicianApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppController(),
      child: const _AppRoot(),
    );
  }
}

/// Separate from [MaintainNexusTechnicianApp] so it can sit *inside* the
/// provider and read the just-created [AppController] to start
/// [DeepLinkService] exactly once — the SMS deep link (Build Plan Phase
/// 2 step 5) needs both the navigator key and the controller to decide
/// where a tapped link should land.
class _AppRoot extends StatefulWidget {
  const _AppRoot();

  @override
  State<_AppRoot> createState() => _AppRootState();
}

class _AppRootState extends State<_AppRoot> {
  final _navigatorKey = GlobalKey<NavigatorState>();
  DeepLinkService? _deepLinks;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _deepLinks ??= DeepLinkService(navigatorKey: _navigatorKey, appController: context.read<AppController>())..start();
  }

  @override
  void dispose() {
    _deepLinks?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppController>(
      builder: (context, app, _) {
        return MaterialApp(
          navigatorKey: _navigatorKey,
          title: 'MaintainNexus Technician',
          debugShowCheckedModeBanner: false,
          themeMode: app.themeMode,
          theme: AppTheme.light,
          darkTheme: AppTheme.dark,
          home: app.signedIn ? const HomeShellScreen() : const SignInScreen(),
        );
      },
    );
  }
}
