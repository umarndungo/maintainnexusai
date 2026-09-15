/// One action recorded locally while offline, waiting to push to the
/// server the moment connectivity returns (spec, Part 1 · Mobile · 04
/// "Offline sync workflow").
class SyncQueueItem {
  SyncQueueItem({required this.workOrderId, required this.description, this.pending = true});

  final String workOrderId;
  final String description;
  bool pending;

  String get label => '$workOrderId · $description';
}
