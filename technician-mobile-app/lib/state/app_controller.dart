import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/sync_queue_item.dart';
import '../models/work_order.dart';
import '../services/api_client.dart';

/// A single, small state container for the whole app — session,
/// simulated connectivity, the work-order list, and the local sync
/// queue described in the spec's offline sync workflow (Part 1 ·
/// Mobile · 04). Backed by the real API (see [ApiClient]) rather than
/// mock data — there's still no local database (Isar/Drift) wired up,
/// so a cold start with no connectivity has nothing cached to show,
/// same limitation the spec's own architecture diagram calls out.
class AppController extends ChangeNotifier {
  AppController({ApiClient? apiClient}) : _api = apiClient ?? ApiClient() {
    _loadThemePreference();
    _restoreSession();
  }

  static const _themePrefKey = 'maintainnexus.theme_mode';
  static const _employeeIdPrefKey = 'maintainnexus.employee_id';
  static const _technicianIdPrefKey = 'maintainnexus.technician_id';

  final ApiClient _api;

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
  //
  // POST /api/v1/auth/login requires a password and returns a 1-hour JWT.
  // Passwords are intentionally not persisted, so an old ID-only session
  // cannot be silently replayed after an app restart.
  // ---------------------------------------------------------------------
  bool _signedIn = false;
  String employeeId = '';
  bool get signedIn => _signedIn;

  /// The roster id (e.g. "TECH-101") resolved from the login response —
  /// see api/auth.py's `_lookup_user`. Null for non-technician demo
  /// logins (engineer-demo, etc.) or if this build's saved session
  /// predates this field. [loadWorkOrders] falls back to the old
  /// unscoped behavior whenever this is null, rather than showing an
  /// empty list.
  String? technicianId;

  bool _mustChangePassword = false;
  bool get mustChangePassword => _mustChangePassword;

  bool _restoringSession = true;
  bool get restoringSession => _restoringSession;

  /// Set on the most recent failed action (login, load, accept,
  /// close-out) so a screen can surface it; cleared at the start of the
  /// next action. Not yet read by any screen in this pass — nothing
  /// crashes without it, but a snackbar wired to this is a natural
  /// follow-up.
  String? lastError;

  Future<void> _restoreSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedId = prefs.getString(_employeeIdPrefKey);
      if (savedId != null && savedId.isNotEmpty) {
        await prefs.remove(_employeeIdPrefKey);
        await prefs.remove(_technicianIdPrefKey);
      }
    } catch (_) {
      // No stored preferences (e.g. first web load) — fall through to sign-in.
    }
    _restoringSession = false;
    notifyListeners();
  }

  /// Best-effort, fire-and-forget — see the call site in [signIn] for why
  /// this is never awaited inline with the rest of the sign-in flow.
  Future<void> _persistSession(String id, String? techId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_employeeIdPrefKey, id);
      if (techId != null) {
        await prefs.setString(_technicianIdPrefKey, techId);
      } else {
        await prefs.remove(_technicianIdPrefKey);
      }
    } catch (_) {
      // No persistence this run (e.g. first web load) — next app start
      // just lands back on the sign-in screen instead of auto-restoring.
    }
  }

  /// Returns true on success. On failure, [lastError] is set and the app
  /// stays on the sign-in screen.
  Future<bool> signIn(String id, String password) async {
    lastError = null;
    try {
      final result = await _api.login(id, password);
      employeeId = id;
      technicianId = result.technicianId;
      _mustChangePassword = result.mustChangePassword;
      _signedIn = true;
      // Fired before the best-effort persistence below (same ordering
      // as setThemeMode) -- a slow or unresponsive SharedPreferences
      // must never stall the UI from reflecting a successful sign-in,
      // which awaiting it inline here would otherwise do.
      notifyListeners();
      unawaited(_persistSession(id, result.technicianId));
      await loadWorkOrders();
      return true;
    } on ApiException catch (exc) {
      lastError = exc.message;
      notifyListeners();
      return false;
    } catch (_) {
      lastError = 'Could not reach the server. Check your connection and try again.';
      notifyListeners();
      return false;
    }
  }

  Future<void> signOut() async {
    _signedIn = false;
    _workOrders.clear();
    _api.accessToken = null;
    technicianId = null;
    _mustChangePassword = false;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_employeeIdPrefKey);
      await prefs.remove(_technicianIdPrefKey);
    } catch (_) {
      // Best-effort.
    }
    notifyListeners();
  }

  /// Wraps an authenticated call and surfaces a 401 to the caller. There is
  /// no refresh-token endpoint, and passwords are not stored for replay.
  Future<T> _authed<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on ApiException catch (exc) {
      if (exc.statusCode == 401 && employeeId.isNotEmpty) {
        rethrow;
      }
      rethrow;
    }
  }

  Future<bool> changePassword(String currentPassword, String newPassword) async {
    lastError = null;
    try {
      await _api.changePassword(currentPassword, newPassword);
      _mustChangePassword = false;
      notifyListeners();
      return true;
    } on ApiException catch (exc) {
      lastError = exc.message;
      notifyListeners();
      return false;
    } catch (_) {
      lastError = 'Could not reach the server. Check your connection and try again.';
      notifyListeners();
      return false;
    }
  }

  // ---------------------------------------------------------------------
  // Simulated connectivity — a stand-in for real OS-level network
  // detection. Toggled from Settings so every offline screen in the
  // spec is actually reachable; the queue it drains below now calls the
  // real API instead of a fake delay.
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
    final items = List<SyncQueueItem>.from(_syncQueue);
    for (final item in items) {
      try {
        await switch (item.action) {
          SyncAction.start => _authed(() => _api.startWorkOrder(item.workOrderId)),
          SyncAction.complete => _authed(
              () => _api.completeWorkOrder(item.workOrderId, notes: item.notes, partsUsed: item.partsUsed),
            ),
        };
        _syncQueue.remove(item);
      } on ApiException catch (exc) {
        // Left in the queue for the next drain attempt; surfaced so the
        // technician isn't left thinking it silently succeeded.
        lastError = 'Sync failed for ${item.workOrderId}: ${exc.message}';
      }
    }
    await loadWorkOrders();
    _syncing = false;
    notifyListeners();
  }

  final List<SyncQueueItem> _syncQueue = [];
  List<SyncQueueItem> get syncQueue => List.unmodifiable(_syncQueue);

  // ---------------------------------------------------------------------
  // Work orders
  // ---------------------------------------------------------------------
  final List<WorkOrder> _workOrders = [];
  List<WorkOrder> get workOrders => List.unmodifiable(_workOrders);

  /// Set by [simulateSyncConflict] to drive the "Sync conflict" screen —
  /// the escalation-while-offline journey (spec, Journey C). Still a
  /// local-only demo affordance: there's no second technician session
  /// in this build to race against for real.
  WorkOrder? conflictWorkOrder;
  String conflictReassignedTo = 'D. Mwangi';

  WorkOrder byId(String id) => _workOrders.firstWhere((w) => w.id == id);

  /// Null-safe lookup — used by the SMS deep-link handler, which can be
  /// tapped for a work order this app hasn't loaded yet. Falls back to
  /// a fresh fetch before giving up, since there's no single-item GET
  /// endpoint on the backend to look one up directly.
  Future<WorkOrder?> tryById(String id) async {
    for (final wo in _workOrders) {
      if (wo.id == id) return wo;
    }
    if (!_signedIn) return null;
    await loadWorkOrders();
    for (final wo in _workOrders) {
      if (wo.id == id) return wo;
    }
    return null;
  }

  /// Fetches every work order plus recent alerts (for risk enrichment),
  /// maps each into a [WorkOrder], and keeps only the ones this
  /// technician can actually act on: DISPATCHED / IN_PROGRESS /
  /// COMPLETED, and — when [technicianId] is known — assigned to them.
  ///
  /// [technicianId] comes back null for a login that didn't resolve to a
  /// roster id (e.g. engineer-demo, or a session persisted before this
  /// field existed); rather than showing an empty list in that case,
  /// this falls back to the old unscoped behavior.
  Future<void> loadWorkOrders() async {
    lastError = null;
    try {
      final results = await Future.wait([
        _authed(() => _api.getWorkOrders()),
        _authed(() => _api.getRecentAlerts()),
      ]);
      final orders = results[0];
      final alerts = results[1];
      final alertsByTaskId = <String, Map<String, dynamic>>{
        for (final alert in alerts)
          if (alert['task_id'] != null) alert['task_id'] as String: alert,
      };

      final mapped = orders
          .map((json) {
            final alertTaskId = json['alert_task_id'] as String?;
            final matchingAlert = alertTaskId != null ? alertsByTaskId[alertTaskId] : null;
            return WorkOrder.fromApi(json, matchingAlert: matchingAlert);
          })
          .where((wo) => wo.status != WorkOrderStatus.scheduled)
          .where((wo) => technicianId == null || wo.assignedTechnicianId == technicianId)
          .toList();

      _workOrders
        ..clear()
        ..addAll(mapped);
      notifyListeners();
    } on ApiException catch (exc) {
      lastError = exc.message;
      notifyListeners();
    } catch (_) {
      lastError = 'Could not reach the server. Check your connection and try again.';
      notifyListeners();
    }
  }

  /// DISPATCHED -> IN_PROGRESS via PATCH .../start. If offline, queues
  /// the action instead — the local status still flips optimistically
  /// so the technician can keep working, and the queue actually reaches
  /// the server once [setOnline] goes back to true.
  Future<void> acceptWorkOrder(String id) async {
    lastError = null;
    if (!_isOnline) {
      _syncQueue.add(SyncQueueItem(workOrderId: id, description: 'accepted', action: SyncAction.start));
      byId(id).status = WorkOrderStatus.inProgress;
      notifyListeners();
      return;
    }
    try {
      await _authed(() => _api.startWorkOrder(id));
      byId(id).status = WorkOrderStatus.inProgress;
      notifyListeners();
    } on ApiException catch (exc) {
      lastError = exc.message;
      notifyListeners();
    }
  }

  void declineWorkOrder(String id) {
    // No "decline" transition exists on the backend's lifecycle
    // (api/workorders.py's allowed map) — a dispatched order can only
    // move to IN_PROGRESS. This stays a local-only remove, same as
    // before; a real decline would need a new backend transition.
    _workOrders.removeWhere((w) => w.id == id);
    notifyListeners();
  }

  void toggleStep(String workOrderId, int index) {
    // No backend endpoint tracks individual checklist steps
    // (WorkOrderRecord has no such column) — this stays purely local
    // and is never queued for sync, unlike accept/close-out below.
    final wo = byId(workOrderId);
    if (index < 0 || index >= wo.checklist.length) return;
    wo.checklist[index].complete = !wo.checklist[index].complete;
    notifyListeners();
  }

  /// IN_PROGRESS -> COMPLETED via PATCH .../complete. photo_object_path
  /// is intentionally never sent — see ApiClient.completeWorkOrder's
  /// docstring; the close-out screen's photo toggle stays UI-only.
  Future<void> submitCloseOut(
    String workOrderId, {
    required List<String> parts,
    String? notes,
    bool photoAttached = false,
  }) async {
    lastError = null;
    final wo = byId(workOrderId);
    if (!_isOnline) {
      _syncQueue.add(
        SyncQueueItem(workOrderId: workOrderId, description: 'closed out', action: SyncAction.complete, notes: notes, partsUsed: parts),
      );
      wo.status = WorkOrderStatus.completed;
      wo.partsUsed = parts;
      wo.notes = notes;
      wo.photoNote = photoAttached ? 'photo-evidence.jpg' : null;
      notifyListeners();
      return;
    }
    try {
      await _authed(() => _api.completeWorkOrder(workOrderId, notes: notes, partsUsed: parts));
      wo.status = WorkOrderStatus.completed;
      wo.partsUsed = parts;
      wo.notes = notes;
      wo.photoNote = photoAttached ? 'photo-evidence.jpg' : null;
      notifyListeners();
    } on ApiException catch (exc) {
      lastError = exc.message;
      notifyListeners();
    }
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
