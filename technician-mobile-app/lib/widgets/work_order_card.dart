import 'package:flutter/material.dart';

import '../models/work_order.dart';
import 'mono_text.dart';
import 'risk_chip.dart';

class WorkOrderCard extends StatelessWidget {
  const WorkOrderCard({super.key, required this.workOrder, required this.onTap});

  final WorkOrder workOrder;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.cardColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: theme.dividerColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: MonoText(
                    workOrder.equipmentLabel,
                    fontSize: 12,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
                RiskChip(riskLevel: workOrder.riskLevel),
              ],
            ),
            const SizedBox(height: 8),
            Text(workOrder.title, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              workOrder.statusNote,
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
