/// Dashboard summary model for Flutter UI.
///
/// Consolidates work order, alert, technician, and inventory data returned
/// from the backend dashboard summary endpoint.
class DashboardSummary {
  final int workOrderCount;
  final int alertCount;
  final List<Technician> availableTechnicians;
  final List<InventoryItem> inventory;

  DashboardSummary({
    required this.workOrderCount,
    required this.alertCount,
    required this.availableTechnicians,
    required this.inventory,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      workOrderCount: json['work_order_count'] as int,
      alertCount: json['alert_count'] as int,
      availableTechnicians: (json['available_technicians'] as List<dynamic>)
          .map((item) => Technician.fromJson(item as Map<String, dynamic>))
          .toList(),
      inventory: (json['inventory'] as List<dynamic>)
          .map((item) => InventoryItem.fromJson(item as Map<String, dynamic>))
          .toList(),
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
    return Technician(
      id: json['id'] as String,
      name: json['name'] as String,
      certs: List<String>.from(json['certs'] as List<dynamic>),
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
