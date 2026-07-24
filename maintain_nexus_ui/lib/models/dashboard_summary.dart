/// Dashboard summary model for Flutter UI.
///
/// Consolidates work order, alert, technician, and inventory data returned
/// from the backend dashboard summary endpoint.
class DashboardSummary {
  final int workOrderCount;
  final int alertCount;
  final int incidentCount;
  final int openWorkOrders;
  final String backendStatus;
  final double downtimeMinutes;
  final double meanRepairTimeMinutes;
  final double uptimePercentage;
  final List<Technician> availableTechnicians;
  final List<InventoryItem> inventory;
  final List<HealthCheck> recentHealthChecks;

  DashboardSummary({
    required this.workOrderCount,
    required this.alertCount,
    required this.incidentCount,
    required this.openWorkOrders,
    required this.downtimeMinutes,
    required this.meanRepairTimeMinutes,
    required this.uptimePercentage,
    required this.backendStatus,
    required this.availableTechnicians,
    required this.inventory,
    required this.recentHealthChecks,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    final availableTechniciansJson = json['available_technicians'];
    final inventoryJson = json['inventory'];
    final recentHealthChecksJson = json['recent_health_checks'];

    return DashboardSummary(
      workOrderCount: (json['work_order_count'] as num?)?.toInt() ?? 0,
      alertCount: (json['alert_count'] as num?)?.toInt() ?? 0,
      incidentCount: (json['incident_count'] as num?)?.toInt() ?? 0,
      openWorkOrders: (json['open_work_orders'] as num?)?.toInt() ?? 0,
      downtimeMinutes: (json['downtime_minutes'] as num?)?.toDouble() ?? 0.0,
      meanRepairTimeMinutes:
          (json['mean_repair_time_minutes'] as num?)?.toDouble() ?? 0.0,
      uptimePercentage: (json['uptime_percentage'] as num?)?.toDouble() ?? 0.0,
      backendStatus: (json['backend_status'] as String?) ?? 'unknown',
      availableTechnicians: (availableTechniciansJson is List<dynamic>
              ? availableTechniciansJson
              : <dynamic>[]) 
          .map((item) => Technician.fromJson(item as Map<String, dynamic>))
          .toList(),
      inventory: (inventoryJson is List<dynamic> ? inventoryJson : <dynamic>[]) 
          .map((item) => InventoryItem.fromJson(item as Map<String, dynamic>))
          .toList(),
      recentHealthChecks: (recentHealthChecksJson is List<dynamic>
              ? recentHealthChecksJson
              : <dynamic>[]) 
          .map((item) => HealthCheck.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Health check model for recent asset telemetry.
class HealthCheck {
  final String equipmentId;
  final double temperature;
  final double vibration;
  final int installationAgeHours;
  final double? riskProbability;
  final String? healthStatus;
  final DateTime checkedAt;

  HealthCheck({
    required this.equipmentId,
    required this.temperature,
    required this.vibration,
    required this.installationAgeHours,
    required this.riskProbability,
    required this.healthStatus,
    required this.checkedAt,
  });

  factory HealthCheck.fromJson(Map<String, dynamic> json) {
    double parseDouble(dynamic value) {
      if (value is num) return value.toDouble();
      if (value is String) return double.tryParse(value) ?? 0.0;
      return 0.0;
    }

    int parseInt(dynamic value) {
      if (value is int) return value;
      if (value is num) return value.toInt();
      if (value is String) return int.tryParse(value) ?? 0;
      return 0;
    }

    DateTime parseCheckedAt(dynamic value) {
      if (value is String) {
        final parsed = DateTime.tryParse(value);
        if (parsed != null) return parsed;
      }
      return DateTime.now().toUtc();
    }

    return HealthCheck(
      equipmentId: json['equipment_id'] as String? ?? 'Unknown',
      temperature: parseDouble(json['temperature']),
      vibration: parseDouble(json['vibration']),
      installationAgeHours: parseInt(json['installation_age_hours']),
      riskProbability: json['risk_probability'] != null
          ? parseDouble(json['risk_probability'])
          : null,
      healthStatus: json['health_status'] as String? ?? 'Unknown',
      checkedAt: parseCheckedAt(json['checked_at']),
    );
  }
}

/// Available technician model for dashboard summary display.
class Technician {
  final String id;
  final String name;
  final List<String> certs;

  Technician({required this.id, required this.name, required this.certs});

  factory Technician.fromJson(Map<String, dynamic> json) {
    final certsJson = json['certs'];
    return Technician(
      id: json['id'] as String? ?? 'Unknown',
      name: json['name'] as String? ?? 'Unknown',
      certs: certsJson is List<dynamic>
          ? List<String>.from(certsJson.map((item) => item.toString()))
          : <String>[],
    );
  }
}

/// Inventory item model for dashboard summary display.
class InventoryItem {
  final String partNumber;
  final int quantityAvailable;
  final bool inStock;

  InventoryItem({
    required this.partNumber,
    required this.quantityAvailable,
    required this.inStock,
  });

  factory InventoryItem.fromJson(Map<String, dynamic> json) {
    return InventoryItem(
      partNumber: json['part_number'] as String,
      quantityAvailable: json['quantity_available'] as int,
      inStock: json['in_stock'] as bool,
    );
  }
}
