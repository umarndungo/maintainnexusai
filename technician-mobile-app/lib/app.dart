import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/home_shell_screen.dart';
import 'screens/change_password_screen.dart';
import 'screens/sign_in_screen.dart';
import 'services/deep_link_service.dart';
import 'state/app_controller.dart';
import 'theme/app_theme.dart';

class MaintainNexusTechnicianApp extends StatelessWidget {
  const MaintainNexusTechnicianApp({super.key, this.appController});

  /// Test-only override — lets widget tests inject an [AppController]
  /// built with a fake [ApiClient] instead of hitting the network. Left
  /// null in real app usage, where a fresh, real-backed controller is
  /// created as before.
  final AppController? appController;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => appController ?? AppController(),
      child: const _AppRoot(),
    );
  }
}

/// Separate from [MaintainNexusTechnicianApp] so it can sit *inside* the
/// provider and read the just-created [AppController] to start
/// [DeepLinkService] exactly once — the SMS deep link (Build Plan Phase
/// 2 step 5) needs both the navigator key and the controller to decide
/// where a tapped link should land.
///
/// Sign-in/out navigate the *existing* Navigator explicitly
/// (pushAndRemoveUntil) rather than relying on MaterialApp's `home:`
/// prop to reactively swap screens. `home` only seeds the Navigator's
/// initial route once; a later rebuild with a different `home` value
/// doesn't re-swap what's on screen, because the Navigator (pinned by
/// `navigatorKey`, needed by DeepLinkService) keeps its existing route
/// stack. Sign-in used to be synchronous, which happened to dodge this
/// — now that it's a real async API call, it needs an explicit push.
class _AppRoot extends StatefulWidget {
  const _AppRoot();

  @override
  State<_AppRoot> createState() => _AppRootState();
}

class _AppRootState extends State<_AppRoot> {
  final _navigatorKey = GlobalKey<NavigatorState>();
  DeepLinkService? _deepLinks;
  AppController? _appController;
  bool _lastSignedIn = false;
  bool _lastMustChangePassword = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_appController != null) return;
    final app = context.read<AppController>();
    _appController = app;
    _lastSignedIn = app.signedIn;
    _lastMustChangePassword = app.mustChangePassword;
    _deepLinks = DeepLinkService(
      navigatorKey: _navigatorKey,
      appController: app,
    )..start();
    app.addListener(_handleAuthChange);
  }

  void _handleAuthChange() {
    final app = _appController;
    if (app == null ||
        (app.signedIn == _lastSignedIn &&
            app.mustChangePassword == _lastMustChangePassword)) {
      return;
    }
    _lastSignedIn = app.signedIn;
    _lastMustChangePassword = app.mustChangePassword;
    final navigator = _navigatorKey.currentState;
    if (navigator == null) return;
    navigator.pushAndRemoveUntil(
      MaterialPageRoute<void>(
        builder: (_) => !app.signedIn
            ? const SignInScreen()
            : app.mustChangePassword
            ? const ChangePasswordScreen()
            : const HomeShellScreen(),
      ),
      (route) => false,
    );
  }

  @override
  void dispose() {
    _appController?.removeListener(_handleAuthChange);
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
          // Still used for the very first build (correct if a restored
          // session already resolved signedIn before first paint);
          // every transition after that goes through _handleAuthChange.
          home: !app.signedIn
              ? const SignInScreen()
              : app.mustChangePassword
              ? const ChangePasswordScreen()
              : const HomeShellScreen(),
        );
      },
    );
  }
}
