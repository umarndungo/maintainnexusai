/// Alert record model for Flutter UI presentation.
///
/// Represents a backend alert payload and metadata needed by the app.
class AlertRecord {
  /// Task ID for the asynchronous alert ingestion job.
  final String? taskId;

  /// Equipment identifier associated with the alert.
  final String equipmentId;

  /// Part number referenced in the alert payload.
  final String partNumber;

  /// Severity of the alert, such as LOW, MEDIUM, or HIGH.
  final String severity;

  /// Failure code included in the maintenance alert.
  final String failureCode;

  /// Timestamp when the alert was received by the backend.
  final String receivedAt;

  AlertRecord({
    required this.taskId,
    required this.equipmentId,
    required this.partNumber,
    required this.severity,
    required this.failureCode,
    required this.receivedAt,
  });

  /// Creates an [AlertRecord] from backend JSON payload.
  ///
  /// Normalizes JSON fields into the UI model so the screen can render a
  /// consistent alert summary.
  factory AlertRecord.fromJson(Map<String, dynamic> json) {
    return AlertRecord(
      taskId: json['task_id'] as String?,
      equipmentId: json['equipment_id'] as String? ?? '',
      partNumber: json['part_number'] as String? ?? '',
      severity: json['severity'] as String? ?? '',
      failureCode: json['failure_code'] as String? ?? '',
      receivedAt: json['received_at'] as String? ?? '',
    );
  }
}
