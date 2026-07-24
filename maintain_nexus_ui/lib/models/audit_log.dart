/// Audit-log entry model for the Flutter UI.
class AuditLogEntry {
  final int id;
  final String eventName;
  final String payload;
  final String timestamp;

  AuditLogEntry({
    required this.id,
    required this.eventName,
    required this.payload,
    required this.timestamp,
  });

  factory AuditLogEntry.fromJson(Map<String, dynamic> json) {
    return AuditLogEntry(
      id: (json['id'] as num?)?.toInt() ?? 0,
      eventName: (json['event_name'] as String?) ?? 'UNKNOWN',
      payload: (json['payload'] as String?) ?? '',
      timestamp: (json['timestamp'] as String?) ?? '',
    );
  }
}
