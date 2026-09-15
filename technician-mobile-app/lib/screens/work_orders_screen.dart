import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';
import '../widgets/connectivity_badge.dart';
import '../widgets/work_order_card.dart';
import 'work_order_detail_screen.dart';

class WorkOrdersScreen extends StatelessWidget {
  const WorkOrdersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppController>();
    final theme = Theme.of(context);
    final orders = app.workOrders;

    return SafeArea(
      bottom: false,
      child: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
            sliver: SliverToBoxAdapter(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('My work orders', style: theme.textTheme.headlineSmall),
                  ConnectivityBadge(isOnline: app.isOnline, syncing: app.syncing),
                ],
              ),
            ),
          ),
          if (!app.isOnline)
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
              sliver: SliverToBoxAdapter(child: _OfflineBanner(count: app.syncQueue.length)),
            ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 140),
            sliver: SliverList.separated(
              itemCount: orders.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final wo = orders[index];
                return WorkOrderCard(
                  workOrder: wo,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => WorkOrderDetailScreen(workOrderId: wo.id)),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final amber = theme.colorScheme.secondary;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: amber.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: amber.withValues(alpha: 0.4)),
      ),
      child: Row(
        children: [
          Icon(Icons.wifi_off_rounded, size: 18, color: amber),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              count == 0
                  ? 'No connection — changes are saved on this phone.'
                  : 'No connection — $count change${count == 1 ? '' : 's'} saved on this phone, waiting to sync.',
              style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface),
            ),
          ),
        ],
      ),
    );
  }
}
