import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';
import '../widgets/mono_text.dart';
import '../widgets/risk_chip.dart';

/// Mockup 7 — Journey C, "the work order moves without the technician."
/// Reached from Settings' "Simulate sync conflict" demo action, since
/// there's no real second session to race against in this build.
class SyncConflictScreen extends StatelessWidget {
  const SyncConflictScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppController>();
    final theme = Theme.of(context);
    final wo = app.conflictWorkOrder;
    if (wo == null) {
      return const Scaffold(body: Center(child: Text('No conflict to show')));
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Sync conflict')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
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
                    Icon(Icons.warning_amber_rounded, size: 18, color: theme.colorScheme.secondary),
                    const SizedBox(width: 10),
                    const Expanded(child: Text('This work order changed while you were offline')),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.cardColor,
                  border: Border.all(color: theme.dividerColor),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(child: MonoText(wo.equipmentLabel, fontSize: 12, color: theme.colorScheme.onSurface.withValues(alpha: 0.6))),
                        RiskChip(riskLevel: wo.riskLevel),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(wo.title, style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    RichText(
                      text: TextSpan(
                        style: theme.textTheme.bodySmall,
                        children: [
                          const TextSpan(text: 'While you were offline, a supervisor escalated this work order and reassigned it to '),
                          TextSpan(text: app.conflictReassignedTo, style: const TextStyle(fontWeight: FontWeight.w700)),
                          const TextSpan(text: ' after the approval SLA passed.'),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'Your queued progress notes were saved to the work order history and are visible to the new assignee. No action from you is needed.',
                style: theme.textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: ElevatedButton(
          onPressed: () {
            app.acknowledgeConflict();
            Navigator.of(context).pop();
          },
          child: const Text('Got it — remove from my list'),
        ),
      ),
    );
  }
}
