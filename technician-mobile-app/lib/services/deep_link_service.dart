import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/material.dart';

import '../screens/deep_link_not_found_screen.dart';
import '../screens/work_order_detail_screen.dart';
import '../state/app_controller.dart';

/// Handles `maintainnexus://work-orders/{id}` taps — the SMS deep link
/// from Build Plan Phase 2 step 5 ("pushing a notification that opens
/// straight to the work order detail screen"). FCM push is wired but
/// inert until a Firebase project exists (see integrations/fcm_client.py
/// on the backend); this is the path that actually has to work tonight.
///
/// Covers both cold start (app opened *by* tapping the link) and warm
/// start (app already running) via [AppLinks.getInitialLink] and
/// [AppLinks.uriLinkStream] respectively.
class DeepLinkService {
  // Assigned via the initializer list, not "this._x" formals, so the
  // public constructor can keep clear, non-underscored named-argument
  // labels (navigatorKey:, appController:) at call sites.
  DeepLinkService({required GlobalKey<NavigatorState> navigatorKey, required AppController appController})
      // ignore: prefer_initializing_formals
      : _navigatorKey = navigatorKey,
        // ignore: prefer_initializing_formals
        _appController = appController;

  final GlobalKey<NavigatorState> _navigatorKey;
  final AppController _appController;
  final AppLinks _appLinks = AppLinks();
  StreamSubscription<Uri>? _subscription;

  Future<void> start() async {
    try {
      final initial = await _appLinks.getInitialLink();
      if (initial != null) _handle(initial);
    } catch (_) {
      // No initial link, or the platform channel isn't ready yet — not
      // an error condition, just nothing to deep-link into.
    }
    _subscription = _appLinks.uriLinkStream.listen(_handle, onError: (_) {});
  }

  void dispose() {
    _subscription?.cancel();
  }

  Future<void> _handle(Uri uri) async {
    if (uri.scheme != 'maintainnexus' || uri.host != 'work-orders') return;
    final workOrderId = uri.pathSegments.isNotEmpty ? uri.pathSegments.first : null;
    if (workOrderId == null || workOrderId.isEmpty) return;

    // Not signed in yet (link tapped cold, before the technician has
    // opened the app once): let sign-in happen first rather than
    // pushing a detail screen on top of it. The link itself doesn't
    // survive that — acceptable for now; a held-link-until-signed-in
    // flow is a separate improvement, out of scope here.
    if (!_appController.signedIn) return;

    // tryById does a real fetch when the id isn't already cached (see
    // AppController.tryById) — that's a network round trip, so this
    // whole handler is async now, unlike the mock-data version.
    final found = await _appController.tryById(workOrderId);

    final navigator = _navigatorKey.currentState;
    if (navigator == null) return;

    final target = found != null
        ? WorkOrderDetailScreen(workOrderId: workOrderId)
        : DeepLinkNotFoundScreen(workOrderId: workOrderId);
    navigator.push(MaterialPageRoute(builder: (_) => target));
  }
}
