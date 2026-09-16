// Smoke test: the app boots to the sign-in screen and a demo sign-in
// lands on the work orders list (spec, Mockups 1 & 2).
//
// Runs against a fake ApiClient (no real network, no Docker backend
// required) rather than the mock data the app used before it was wired
// to the real API — see lib/services/api_client.dart and
// lib/state/app_controller.dart.
//
// Uses fixed pump()s rather than pumpAndSettle() because the connectivity
// badge's dot animates indefinitely by design (a subtle live-status
// pulse), which pumpAndSettle would wait forever for.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:technician_mobile_app/app.dart';
import 'package:technician_mobile_app/services/api_client.dart';
import 'package:technician_mobile_app/state/app_controller.dart';
import 'package:technician_mobile_app/screens/change_password_screen.dart';

/// Records calls and returns canned data instead of hitting the network
/// — same shapes the real backend returns (see api/workorders.py,
/// api/maintenance.py's /alerts/recent).
class FakeApiClient implements ApiClient {
  @override
  String? accessToken;

  @override
  String get baseUrl => 'http://fake';

  @override
  Future<LoginResult> login(String employeeId, String password) async {
    accessToken = 'fake-token';
    return const LoginResult(accessToken: 'fake-token', name: 'Demo Technician', technicianId: 'TECH-101');
  }

  @override
  Future<void> changePassword(String currentPassword, String newPassword) async {}

  @override
  Future<List<Map<String, dynamic>>> getWorkOrders() async => [
        {
          'work_order_id': 'WO-TEST01',
          'equipment_id': 'PUMP-14',
          'assigned_technician_id': 'TECH-101',
          'reserved_part': 'Seal kit SK-14B',
          'status': 'DISPATCHED',
          'created_at': DateTime.now().toIso8601String(),
          'duration_seconds': 360,
          'alert_task_id': 'alert-1',
        },
      ];

  @override
  Future<List<Map<String, dynamic>>> getRecentAlerts() async => [
        {
          'task_id': 'alert-1',
          'equipment_id': 'PUMP-14',
          'severity': 'HIGH',
          'failure_code': 'ERR_VIBRATION',
          'risk_probability': 0.87,
        },
      ];

  @override
  Future<Map<String, dynamic>> startWorkOrder(String workOrderId) async => {
        'work_order_id': workOrderId,
        'status': 'IN_PROGRESS',
        'event_id': 1,
      };

  @override
  Future<Map<String, dynamic>> completeWorkOrder(String workOrderId, {String? notes, List<String> partsUsed = const []}) async => {
        'work_order_id': workOrderId,
        'status': 'COMPLETED',
        'event_id': 2,
      };
}

void main() {
  // Standard shared_preferences test setup: without this, plugin calls
  // hang forever under `flutter test` (no platform channel is
  // registered to answer them) rather than throwing — AppController's
  // own try/catch around persistence can't save it from a call that
  // never actually completes either way.
  SharedPreferences.setMockInitialValues({});

  testWidgets('boots to sign-in and reaches My work orders', (WidgetTester tester) async {
    final appController = AppController(apiClient: FakeApiClient());

    await tester.pumpWidget(MaintainNexusTechnicianApp(appController: appController));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Sign in'), findsWidgets);

    final signInButton = find.widgetWithText(ElevatedButton, 'Sign in');
    await tester.ensureVisible(signInButton);
    await tester.pump();
    await tester.tap(signInButton);
    // Sign-in is a real (fake-backed) async chain now: login -> flip
    // signedIn -> loadWorkOrders (two parallel calls) -> notifyListeners.
    // Several pumps give each hop a turn instead of one big delay.
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('My work orders'), findsOneWidget);
    expect(find.text('Excess vibration detected'), findsOneWidget);
  });

  testWidgets('forced password change appears before work orders', (WidgetTester tester) async {
    final appController = AppController(apiClient: _MustChangeFakeApiClient());

    await tester.pumpWidget(MaintainNexusTechnicianApp(appController: appController));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    final signInButton = find.widgetWithText(ElevatedButton, 'Sign in');
    await tester.ensureVisible(signInButton);
    await tester.tap(signInButton);
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byType(ChangePasswordScreen), findsOneWidget);
    expect(find.text('My work orders'), findsNothing);
  });
}

class _MustChangeFakeApiClient extends FakeApiClient {
  @override
  Future<LoginResult> login(String employeeId, String password) async {
    accessToken = 'fake-token';
    return const LoginResult(
      accessToken: 'fake-token',
      name: 'Demo Technician',
      technicianId: 'TECH-101',
      mustChangePassword: true,
    );
  }
}
