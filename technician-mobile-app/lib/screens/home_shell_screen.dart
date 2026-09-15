import 'package:flutter/material.dart';

import '../widgets/app_shell.dart';
import 'insights_screen.dart';
import 'settings_screen.dart';
import 'sync_queue_screen.dart';
import 'work_orders_screen.dart';

/// Hosts the four nav-bar destinations behind the floating capsule bar.
class HomeShellScreen extends StatefulWidget {
  const HomeShellScreen({super.key});

  @override
  State<HomeShellScreen> createState() => _HomeShellScreenState();
}

class _HomeShellScreenState extends State<HomeShellScreen> {
  int _index = 0;

  static const _screens = [
    WorkOrdersScreen(),
    SyncQueueScreen(),
    InsightsScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return AppShell(
      currentIndex: _index,
      onDestinationSelected: (i) => setState(() => _index = i),
      body: IndexedStack(index: _index, children: _screens),
    );
  }
}
