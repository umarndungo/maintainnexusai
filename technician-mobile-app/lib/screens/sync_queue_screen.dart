import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';
import '../widgets/connectivity_badge.dart';

/// Mirrors Mockup 6 ("Offline mode") — reachable any time from the
/// Queue tab, not only while actually offline, so the "nothing here
/// needs your attention" state is visible too.
class SyncQueueScreen extends StatelessWidget {
  const SyncQueueScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppController>();
    final theme = Theme.of(context);
    final queue = app.syncQueue;

    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('My work orders', style: theme.textTheme.headlineSmall),
                ConnectivityBadge(isOnline: app.isOnline, syncing: app.syncing),
              ],
            ),
            const SizedBox(height: 16),
            if (!app.isOnline)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: theme.colorScheme.secondary.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: theme.colorScheme.secondary.withValues(alpha: 0.4)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.wifi_off_rounded, size: 18, color: theme.colorScheme.secondary),
                    const SizedBox(width: 10),
                    const Expanded(child: Text('No connection — changes are saved on this phone.')),
                  ],
                ),
              ),
            const SizedBox(height: 20),
            Text('QUEUED & WAITING TO SYNC', style: theme.textTheme.labelSmall),
            const SizedBox(height: 12),
            Expanded(
              child: queue.isEmpty
                  ? _EmptyQueue(isOnline: app.isOnline)
                  : ListView.separated(
                      itemCount: queue.length,
                      separatorBuilder: (_, _) => Divider(color: theme.dividerColor, height: 24),
                      itemBuilder: (context, index) {
                        final item = queue[index];
                        return Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(child: Text(item.label, style: theme.textTheme.bodyMedium)),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: theme.colorScheme.secondary.withValues(alpha: 0.16),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text('QUEUED', style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.secondary)),
                            ),
                          ],
                        );
                      },
                    ),
            ),
            const SizedBox(height: 12),
            Text(
              app.isOnline
                  ? 'Everything is synced. Actions taken offline will appear here until they push.'
                  : "Everything above is safe on this phone. It will upload automatically the moment you're back in signal — no action needed.",
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 140),
          ],
        ),
      ),
    );
  }
}

class _EmptyQueue extends StatelessWidget {
  const _EmptyQueue({required this.isOnline});

  final bool isOnline;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.cloud_done_rounded, size: 32, color: theme.colorScheme.onSurface.withValues(alpha: 0.3)),
          const SizedBox(height: 12),
          Text(isOnline ? 'All caught up' : 'Nothing queued yet', style: theme.textTheme.bodyMedium),
        ],
      ),
    );
  }
}
