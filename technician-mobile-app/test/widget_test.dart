// Smoke test: the app boots to the sign-in screen and a demo sign-in
// lands on the work orders list (spec, Mockups 1 & 2).
//
// Uses fixed pump()s rather than pumpAndSettle() because the connectivity
// badge's dot animates indefinitely by design (a subtle live-status
// pulse), which pumpAndSettle would wait forever for.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:technician_mobile_app/app.dart';

void main() {
  testWidgets('boots to sign-in and reaches My work orders', (WidgetTester tester) async {
    await tester.pumpWidget(const MaintainNexusTechnicianApp());
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Sign in'), findsWidgets);

    final signInButton = find.widgetWithText(ElevatedButton, 'Sign in');
    await tester.ensureVisible(signInButton);
    await tester.pump();
    await tester.tap(signInButton);
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('My work orders'), findsOneWidget);
    expect(find.text('Bearing vibration exceeds threshold'), findsOneWidget);
  });
}
