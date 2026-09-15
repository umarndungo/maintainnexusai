/// Which real backend call a queued offline action replays once
/// connectivity returns (see AppController._drainQueue). Checklist-step
/// toggles have no backend endpoint at all (WorkOrderRecord doesn't
/// track individual steps) and so are never queued — only these two
/// actually reach the server.
enum SyncAction { start, complete }

/// One action recorded locally while offline, waiting to push to the
/// server the moment connectivity returns (spec, Part 1 · Mobile · 04
/// "Offline sync workflow").
class SyncQueueItem {
  SyncQueueItem({
    required this.workOrderId,
    required this.description,
    required this.action,
    this.notes,
    this.partsUsed = const [],
    this.pending = true,
  });

  final String workOrderId;
  final String description;
  final SyncAction action;

  /// Only used when [action] is [SyncAction.complete].
  final String? notes;
  final List<String> partsUsed;

  bool pending;

  String get label => '$workOrderId · $description';
}
