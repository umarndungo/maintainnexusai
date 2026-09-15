import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../data/mock_data.dart';
import '../models/sync_queue_item.dart';
import '../models/work_order.dart';

/// A single, small state container for the whole demo — session,
/// simulated connectivity, the work-order list, and the local sync
/// queue described in the spec's offline sync workflow (Part 1 ·
/// Mobile · 04). There is no real backend or local database wired up
/// (see README.md "What's not implemented yet") — this stands in for
/// the local store (Isar/Drift) and background sync queue in the
/// architecture diagram so every screen has real, changing state to
/// render against.
class AppController extends ChangeNotifier {
  AppController() {
    _loadThemePreference();
  }

  static const _themePrefKey = 'maintainnexus.theme_mode';

  // ---------------------------------------------------------------------
  // Theme
  // ---------------------------------------------------------------------
  ThemeMode _themeMode = ThemeMode.dark;
  ThemeMode get themeMode => _themeMode;

  Future<void> _loadThemePreference() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString(_themePrefKey);
      if (saved == 'light') {
        _themeMode = ThemeMode.light;
      } else if (saved == 'system') {
        _themeMode = ThemeMode.system;
      } else {
        _themeMode = ThemeMode.dark;
      }
      notifyListeners();
    } catch (_) {
      // Preferences unavailable (e.g. first web load) — keep the default.
    }
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_themePrefKey, mode.name);
    } catch (_) {
      // Best-effort persistence only.
    }
  }

  // ---------------------------------------------------------------------
  // Session
  // ---------------------------------------------------------------------
  bool _signedIn = false;
  String employeeId = '';
  bool get signedIn => _signedIn;

  void signIn(String id) {
    employeeId = id;
    _signedIn = true;
    notifyListeners();
  }

  void signOut() {
    _signedIn = false;
    notifyListeners();
  }

  // ---------------------------------------------------------------------
  // Simulated connectivity — a stand-in for the real network/offline
  // detection the background sync queue would use. Toggled from
  // Settings so every offline screen in the spec is actually reachable.
  // ---------------------------------------------------------------------
  bool _isOnline = true;
  bool get isOnline => _isOnline;
  bool _syncing = false;
  bool get syncing => _syncing;

  Future<void> setOnline(bool online) async {
    if (_isOnline == online) return;
    _isOnline = online;
    notifyListeners();
    if (online && _syncQueue.isNotEmpty) {
      await _drainQueue();
    }
  }

  Future<void> _drainQueue() async {
    _syncing = true;
    notifyListeners();
    await Future<void>.delayed(const Duration(milliseconds: 900));
    _syncQueue.clear();
    _syncing = false;
    notifyListeners();
  }

  final List<SyncQueueItem> _syncQueue = [];
  List<SyncQueueItem> get syncQueue => List.unmodifiable(_syncQueue);

  void _queueIfOffline(String workOrderId, String description) {
    if (!_isOnline) {
      _syncQueue.add(SyncQueueItem(workOrderId: workOrderId, description: description));
    }
  }

  // ---------------------------------------------------------------------
  // Work orders
  // ---------------------------------------------------------------------
  final List<WorkOrder> _workOrders = MockData.workOrders();
  List<WorkOrder> get workOrders => List.unmodifiable(_workOrders);

  /// Set by [simulateSyncConflict] to drive the "Sync conflict" screen —
  /// the escalation-while-offline journey (spec, Journey C).
  WorkOrder? conflictWorkOrder;
  String conflictReassignedTo = 'D. Mwangi';

  WorkOrder byId(String id) => _workOrders.firstWhere((w) => w.id == id);

  /// Null-safe lookup — used by the SMS deep link handler, which can be
  /// tapped for a work order this phone hasn't cached locally yet (this
  /// build has no live API sync; see README.md). Prefer this over
  /// [byId] whenever the id didn't come from this app's own list.
  WorkOrder? tryById(String id) {
    for (final wo in _workOrders) {
      if (wo.id == id) return wo;
    }
    return null;
  }

  void acceptWorkOrder(String id) {
    final wo = byId(id);
    wo.status = WorkOrderStatus.inProgress;
    _queueIfOffline(id, 'accepted');
    notifyListeners();
  }

  void declineWorkOrder(String id) {
    _workOrders.removeWhere((w) => w.id == id);
    notifyListeners();
  }

  void toggleStep(String workOrderId, int index) {
    final wo = byId(workOrderId);
    if (index < 0 || index >= wo.checklist.length) return;
    wo.checklist[index].complete = !wo.checklist[index].complete;
    _queueIfOffline(workOrderId, 'step ${index + 1} ${wo.checklist[index].complete ? 'complete' : 'reopened'}');
    notifyListeners();
  }

  void submitCloseOut(String workOrderId, {required List<String> parts, String? notes, bool photoAttached = false}) {
    final wo = byId(workOrderId);
    wo.status = WorkOrderStatus.completed;
    wo.partsUsed = parts;
    wo.notes = notes;
    wo.photoNote = photoAttached ? 'photo-evidence.jpg' : null;
    _queueIfOffline(workOrderId, 'closed out');
    notifyListeners();
  }

  /// Demo affordance (reached from Settings) for the escalation-while-
  /// offline journey — there's no real second technician/session to
  /// race against, so this simulates the server-side event the app
  /// would otherwise learn about from the events stream (SSE).
  void simulateSyncConflict() {
    if (_workOrders.isEmpty) return;
    conflictWorkOrder = _workOrders.first;
    notifyListeners();
  }

  void acknowledgeConflict() {
    if (conflictWorkOrder != null) {
      _workOrders.removeWhere((w) => w.id == conflictWorkOrder!.id);
    }
    conflictWorkOrder = null;
    notifyListeners();
  }
}
