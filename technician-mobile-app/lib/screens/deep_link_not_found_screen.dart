import 'package:flutter/material.dart';

import '../widgets/mono_text.dart';

/// Shown when an SMS deep link (maintainnexus://work-orders/{id}) points
/// at a work order this phone hasn't cached locally. Expected tonight —
/// this build has no live API sync yet (README.md) — so this is a
/// straightforward "not yet", not an error page.
class DeepLinkNotFoundScreen extends StatelessWidget {
  const DeepLinkNotFoundScreen({super.key, required this.workOrderId});

  final String workOrderId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Work order')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Icon(Icons.link_off_rounded, size: 40, color: theme.colorScheme.onSurface.withValues(alpha: 0.4)),
              const SizedBox(height: 16),
              Text('Not synced to this phone yet', style: theme.textTheme.titleLarge, textAlign: TextAlign.center),
              const SizedBox(height: 8),
              MonoText(workOrderId, fontSize: 12, color: theme.colorScheme.onSurface.withValues(alpha: 0.55)),
              const SizedBox(height: 8),
              Text(
                'This link points to a work order this app hasn\'t cached. Open My work orders to sync, then use this link again.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
                child: const Text('Go to My work orders'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
