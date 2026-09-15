import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/work_order.dart';
import '../state/app_controller.dart';

/// A lightweight stats view in the fourth nav slot — styled after the
/// stat-card grid in the reference screenshot's Admin Panel frame.
/// Numbers are derived from the same mock work-order list every other
/// screen reads, not a separate dataset.
class InsightsScreen extends StatelessWidget {
  const InsightsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppController>();
    final theme = Theme.of(context);
    final orders = app.workOrders;
    final active = orders.where((w) => w.status == WorkOrderStatus.inProgress).length;
    final pending = orders.where((w) => w.status == WorkOrderStatus.dispatched).length;
    final completed = orders.where((w) => w.status == WorkOrderStatus.completed).length;
    final highRisk = orders.where((w) => w.riskLevel.toUpperCase() == 'HIGH' && w.status != WorkOrderStatus.completed).length;

    return SafeArea(
      bottom: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 140),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Insights', style: theme.textTheme.headlineSmall),
            const SizedBox(height: 4),
            Text('Today · your assigned work', style: theme.textTheme.bodySmall),
            const SizedBox(height: 20),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.5,
              children: [
                _StatCard(label: 'In progress', value: '$active'),
                _StatCard(label: 'Pending accept', value: '$pending'),
                _StatCard(label: 'Completed today', value: '$completed'),
                _StatCard(label: 'High risk open', value: '$highRisk', accent: highRisk > 0),
              ],
            ),
            const SizedBox(height: 28),
            Text('WORK ORDER PROGRESS', style: theme.textTheme.labelSmall),
            const SizedBox(height: 12),
            for (final wo in orders) ...[
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(wo.title, style: theme.textTheme.bodyMedium, overflow: TextOverflow.ellipsis),
                        Text(
                          wo.checklist.isEmpty ? '—' : '${wo.completedStepCount}/${wo.checklist.length}',
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(999),
                      child: LinearProgressIndicator(
                        value: wo.checklist.isEmpty ? 0 : wo.completedStepCount / wo.checklist.length,
                        minHeight: 6,
                        backgroundColor: theme.dividerColor,
                        color: theme.colorScheme.secondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value, this.accent = false});

  final String label;
  final String value;
  final bool accent;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent ? theme.colorScheme.error.withValues(alpha: 0.4) : theme.dividerColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(color: accent ? theme.colorScheme.error : null),
          ),
          const SizedBox(height: 2),
          Text(label, style: theme.textTheme.bodySmall),
        ],
      ),
    );
  }
}
