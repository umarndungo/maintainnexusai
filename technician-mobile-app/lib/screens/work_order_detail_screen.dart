import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/work_order.dart';
import '../state/app_controller.dart';
import '../widgets/mono_text.dart';
import '../widgets/risk_chip.dart';
import 'active_task_screen.dart';

class WorkOrderDetailScreen extends StatelessWidget {
  const WorkOrderDetailScreen({super.key, required this.workOrderId});

  final String workOrderId;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppController>();
    final theme = Theme.of(context);
    final wo = app.byId(workOrderId);

    return Scaffold(
      appBar: AppBar(
        title: MonoText(wo.equipmentLabel, fontSize: 13, color: theme.colorScheme.onSurface),
        actions: [Padding(padding: const EdgeInsets.only(right: 16), child: Center(child: RiskChip(riskLevel: wo.riskLevel)))],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(wo.title, style: theme.textTheme.headlineSmall),
              const SizedBox(height: 4),
              MonoText(
                'Work order #${wo.id} · Risk score ${wo.riskScore.toStringAsFixed(2)}',
                fontSize: 12,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.55),
              ),
              const SizedBox(height: 28),
              if (wo.riskDrivers.isNotEmpty) ...[
                Text('WHY THIS WAS FLAGGED', style: theme.textTheme.labelSmall),
                const SizedBox(height: 4),
                Container(
                  decoration: BoxDecoration(
                    border: Border.all(color: theme.dividerColor),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    children: [
                      for (int i = 0; i < wo.riskDrivers.length; i++)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(wo.riskDrivers[i].label, style: theme.textTheme.bodyMedium),
                              MonoText(
                                wo.riskDrivers[i].value,
                                fontWeight: FontWeight.w600,
                                color: wo.riskDrivers[i].flagged ? _riskColor(context, wo.riskLevel) : null,
                              ),
                            ],
                          ),
                        ),
                    ],
                  ).divideWith(theme.dividerColor),
                ),
                const SizedBox(height: 24),
              ],
              if (wo.reservedPart != null) ...[
                Text('PARTS RESERVED', style: theme.textTheme.labelSmall),
                const SizedBox(height: 8),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: theme.cardColor,
                    border: Border.all(color: theme.dividerColor),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.inventory_2_rounded, size: 18, color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
                      const SizedBox(width: 10),
                      Expanded(child: Text(wo.reservedPart!, style: theme.textTheme.bodyMedium)),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
      bottomNavigationBar: wo.status == WorkOrderStatus.completed
          ? null
          : SafeArea(
              minimum: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: Row(
                children: [
                  if (wo.status != WorkOrderStatus.inProgress)
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          app.declineWorkOrder(wo.id);
                          Navigator.of(context).pop();
                        },
                        child: const Text('Decline'),
                      ),
                    ),
                  if (wo.status != WorkOrderStatus.inProgress) const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: ElevatedButton(
                      onPressed: () {
                        if (wo.status != WorkOrderStatus.inProgress) {
                          app.acceptWorkOrder(wo.id);
                        }
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => ActiveTaskScreen(workOrderId: wo.id)),
                        );
                      },
                      child: Text(wo.status == WorkOrderStatus.inProgress ? 'Continue task' : 'Accept & start'),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Color _riskColor(BuildContext context, String level) {
    switch (level.toUpperCase()) {
      case 'HIGH':
        return Theme.of(context).colorScheme.error;
      default:
        return Theme.of(context).colorScheme.secondary;
    }
  }
}

extension _DivideColumn on Column {
  Widget divideWith(Color color) {
    final divided = <Widget>[];
    for (int i = 0; i < children.length; i++) {
      divided.add(children[i]);
      if (i != children.length - 1) divided.add(Divider(color: color, height: 1));
    }
    return Column(children: divided);
  }
}
