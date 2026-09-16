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
    this.assignedTechnicianId,
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

  /// The roster id (e.g. "TECH-101") this order is assigned to — see
  /// api/technicians.py. Used by AppController to scope the list to the
  /// signed-in technician.
  final String? assignedTechnicianId;

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

  /// Builds a [WorkOrder] from the real backend's
  /// `GET /api/v1/maintenance/work-orders` row shape (work_order_id,
  /// equipment_id, assigned_technician_id, reserved_part, status,
  /// created_at, duration_seconds, alert_task_id). [matchingAlert], when
  /// provided, is the `GET /api/v1/alerts/recent` row whose `task_id`
  /// equals this order's `alert_task_id` — the only place risk info
  /// actually lives; a work order with no match (alert aged out of the
  /// recent window, or not alert-triggered) gets the same LOW/neutral
  /// defaults the UI already treats as "no risk data" (see
  /// AppColors.riskColor's fallback).
  factory WorkOrder.fromApi(Map<String, dynamic> json, {Map<String, dynamic>? matchingAlert}) {
    final equipmentId = json['equipment_id'] as String? ?? 'UNKNOWN';
    final dashIndex = equipmentId.indexOf('-');
    final equipmentType = dashIndex > 0 ? equipmentId.substring(0, dashIndex) : equipmentId;
    final equipmentCode = dashIndex > 0 ? equipmentId.substring(dashIndex + 1) : equipmentId;

    final status = _statusFromApi(json['status'] as String? ?? '');
    final elapsed = _relativeFromSeconds((json['duration_seconds'] as num?)?.toInt() ?? 0);

    final riskProbability = (matchingAlert?['risk_probability'] as num?)?.toDouble();
    final severity = matchingAlert?['severity'] as String?;
    final failureCode = matchingAlert?['failure_code'] as String?;

    return WorkOrder(
      id: json['work_order_id'] as String? ?? '',
      equipmentType: equipmentType,
      equipmentCode: equipmentCode,
      // WorkOrderRecord has no station column yet (see the decision-engine
      // work this session — only LoadingPoint/EquipmentReading carry one).
      station: '—',
      title: failureCode != null ? _titleFromFailureCode(failureCode) : '$equipmentId needs attention',
      riskLevel: severity ?? 'LOW',
      riskScore: riskProbability ?? 0.0,
      status: status,
      statusNote: status == WorkOrderStatus.scheduled ? 'Awaiting approval' : '${_statusVerb(status)} $elapsed',
      assignedTechnicianId: json['assigned_technician_id'] as String?,
      reservedPart: json['reserved_part'] as String?,
      // GET /alerts/recent doesn't expose top_features -- see
      // ApiClient.getRecentAlerts's docstring. Empty here renders the
      // screen's existing "no drivers" state rather than fabricating data.
      riskDrivers: const [],
    );
  }

  static WorkOrderStatus _statusFromApi(String raw) {
    switch (raw) {
      case 'DISPATCHED':
        return WorkOrderStatus.dispatched;
      case 'IN_PROGRESS':
        return WorkOrderStatus.inProgress;
      case 'COMPLETED':
        return WorkOrderStatus.completed;
      default:
        // PENDING_APPROVAL / APPROVED / ESCALATED / REJECTED -- not yet
        // actionable by a technician; folded into "scheduled" rather
        // than adding enum values the UI has no treatment for.
        return WorkOrderStatus.scheduled;
    }
  }

  static String _statusVerb(WorkOrderStatus status) {
    switch (status) {
      case WorkOrderStatus.dispatched:
        return 'Dispatched';
      case WorkOrderStatus.inProgress:
        return 'Started';
      case WorkOrderStatus.completed:
        return 'Completed';
      case WorkOrderStatus.scheduled:
        return 'Scheduled';
    }
  }

  static String _relativeFromSeconds(int seconds) {
    if (seconds < 60) return 'just now';
    final minutes = seconds ~/ 60;
    if (minutes < 60) return '$minutes min ago';
    final hours = minutes ~/ 60;
    if (hours < 24) return '$hours hr ago';
    return '${hours ~/ 24} d ago';
  }

  static String _titleFromFailureCode(String failureCode) {
    switch (failureCode) {
      case 'ERR_OVERHEAT':
        return 'Overheating detected';
      case 'ERR_VIBRATION':
        return 'Excess vibration detected';
      case 'ERR_SEAL_LEAK':
        return 'Seal leak detected';
      default:
        return 'Fault detected';
    }
  }
}
