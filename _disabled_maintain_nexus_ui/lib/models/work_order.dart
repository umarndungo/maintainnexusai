/// Work order model for Flutter UI data transfer and backend request mapping.
///
/// Serializes to the backend request format and parses backend response JSON.
class WorkOrder {
  /// Backend work order identifier returned after creation.
  final String id;

  /// Equipment identifier for the work order payload.
  final String equipmentId;

  /// Technician assigned to the work order.
  final String technicianId;

  /// Part number being requested or reserved for the work order.
  final String partNumber;

  /// Work order status returned by the backend.
  final String status;

  /// Timestamp when this work order was created.
  final DateTime? createdAt;

  /// Cached duration in seconds if the backend does not provide a createdAt timestamp.
  final int durationSeconds;

  WorkOrder({
    required this.id,
    required this.equipmentId,
    required this.technicianId,
    required this.partNumber,
    required this.status,
    required this.createdAt,
    required this.durationSeconds,
  });

  /// Elapsed time in seconds since creation, derived from [createdAt].
  ///
  /// Falls back to [durationSeconds] only when the timestamp is unavailable.
  int get elapsedSeconds {
    if (createdAt == null) {
      return durationSeconds;
    }
    return DateTime.now().difference(createdAt!).inSeconds;
  }

  /// Creates a [WorkOrder] model from JSON returned by the backend.
  ///
  /// Handles both backend response field names and fallback keys to support
  /// slightly different API payload shapes.
  factory WorkOrder.fromJson(Map<String, dynamic> json) {
    return WorkOrder(
      id: json['work_order_id'] ?? json['id'] ?? '',
      equipmentId: json['equipment_id'] ?? '',
      technicianId:
          json['assigned_technician_id'] ?? json['technician_id'] ?? '',
      partNumber: json['reserved_part'] ?? json['part_number'] ?? '',
      status: json['status'] ?? 'UNKNOWN',
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String).toLocal()
          : null,
      durationSeconds: json['duration_seconds'] as int? ?? 0,
    );
  }

  /// Serializes the work order into the backend request format.
  ///
  /// Only the required fields for creation are included in the outgoing JSON.
  Map<String, dynamic> toJson() => {
    'equipment_id': equipmentId,
    'technician_id': technicianId,
    'part_number': partNumber,
  };
}
