import 'checklist_step.dart';

/// Where a work order sits in its lifecycle — mirrors the lifecycle
/// events the backend hash-chains into the audit log (spec, Part 2 ·
/// Web · 03 "Live execution to close-out").
enum WorkOrderStatus { scheduled, dispatched, inProgress, completed }

/// One risk driver shown on the work order detail screen — plain-language,
/// straight from the model's `top_features` output, never a bare score
/// (spec, "Principles": "The model explains itself").
class RiskDriver {
  const RiskDriver({required this.label, required this.value, this.flagged = true});

  final String label;
  final String value;

  /// Whether this driver reads as a call-out (rendered in the risk color)
  /// or a neutral supporting fact.
  final bool flagged;
}

class WorkOrder {
  WorkOrder({
    required this.id,
    required this.equipmentType,
    required this.equipmentCode,
    required this.station,
    required this.title,
    required this.riskLevel,
    required this.riskScore,
    required this.status,
    required this.statusNote,
    this.approvedBy,
    this.riskDrivers = const [],
    this.reservedPart,
    this.checklist = const [],
    this.startedNote,
    List<String>? partsUsed,
    this.notes,
  }) : partsUsed = partsUsed ?? (reservedPart != null ? [reservedPart] : []);

  final String id;
  final String equipmentType;
  final String equipmentCode;
  final String station;
  final String title;

  /// LOW · MEDIUM · HIGH — same three functional colors everywhere.
  final String riskLevel;
  final double riskScore;

  WorkOrderStatus status;

  /// Short line under the title on the list screen, e.g.
  /// "Dispatched 6 min ago · Approved by station engineer".
  final String statusNote;
  final String? approvedBy;
  final List<RiskDriver> riskDrivers;
  final String? reservedPart;
  final List<ChecklistStep> checklist;
  final String? startedNote;

  List<String> partsUsed;
  String? notes;
  String? photoNote;

  String get equipmentLabel => '$equipmentType · $equipmentCode · $station';

  int get completedStepCount => checklist.where((s) => s.complete).length;

  bool get allStepsComplete => checklist.isNotEmpty && completedStepCount == checklist.length;

  String get statusLabel {
    switch (status) {
      case WorkOrderStatus.scheduled:
        return 'Scheduled';
      case WorkOrderStatus.dispatched:
        return 'Dispatched';
      case WorkOrderStatus.inProgress:
        return 'In progress';
      case WorkOrderStatus.completed:
        return 'Completed';
    }
  }
}
