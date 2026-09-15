import 'package:flutter/material.dart';

import '../models/work_order.dart';

/// The neutral work-order-status pill (Scheduled / Dispatched / In
/// progress / Completed) — distinct from [RiskChip], which is always
/// red/amber/green. This one uses the theme's surface tones so it
/// never competes with the risk color for attention.
class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.status});

  final WorkOrderStatus status;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final bool emphasized = status == WorkOrderStatus.inProgress;
    final Color bg = emphasized ? scheme.primary : scheme.onSurface.withValues(alpha: 0.08);
    final Color fg = emphasized ? scheme.onPrimary : scheme.onSurface.withValues(alpha: 0.75);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
      child: Text(
        _label(status),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: fg),
      ),
    );
  }

  String _label(WorkOrderStatus status) {
    switch (status) {
      case WorkOrderStatus.scheduled:
        return 'SCHEDULED';
      case WorkOrderStatus.dispatched:
        return 'PENDING';
      case WorkOrderStatus.inProgress:
        return 'IN PROGRESS';
      case WorkOrderStatus.completed:
        return 'COMPLETED';
    }
  }
}
