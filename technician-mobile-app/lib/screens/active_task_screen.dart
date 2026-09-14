import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';
import '../widgets/mono_text.dart';
import '../widgets/status_pill.dart';
import 'close_out_screen.dart';

class ActiveTaskScreen extends StatelessWidget {
  const ActiveTaskScreen({super.key, required this.workOrderId});

  final String workOrderId;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppController>();
    final theme = Theme.of(context);
    final wo = app.byId(workOrderId);
    final nextIncomplete = wo.checklist.indexWhere((s) => !s.complete);

    return Scaffold(
      appBar: AppBar(
        title: MonoText(wo.equipmentLabel, fontSize: 13, color: theme.colorScheme.onSurface),
        actions: [Padding(padding: const EdgeInsets.only(right: 16), child: Center(child: StatusPill(status: wo.status)))],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(wo.title, style: theme.textTheme.headlineSmall),
              const SizedBox(height: 4),
              Text(wo.startedNote ?? 'Not started yet', style: theme.textTheme.bodySmall),
              const SizedBox(height: 24),
              Expanded(
                child: ListView.separated(
                  itemCount: wo.checklist.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 4),
                  itemBuilder: (context, index) {
                    final step = wo.checklist[index];
                    return InkWell(
                      onTap: () => app.toggleStep(wo.id, index),
                      borderRadius: BorderRadius.circular(12),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              step.complete ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                              size: 20,
                              color: step.complete
                                  ? theme.colorScheme.secondary
                                  : theme.colorScheme.onSurface.withValues(alpha: 0.35),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                step.label,
                                style: theme.textTheme.bodyLarge?.copyWith(
                                  decoration: step.complete ? TextDecoration.lineThrough : null,
                                  color: step.complete ? theme.colorScheme.onSurface.withValues(alpha: 0.45) : null,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: ElevatedButton(
          onPressed: () {
            if (nextIncomplete != -1) {
              app.toggleStep(wo.id, nextIncomplete);
              return;
            }
            Navigator.of(context).push(MaterialPageRoute(builder: (_) => CloseOutScreen(workOrderId: wo.id)));
          },
          child: Text(nextIncomplete != -1 ? 'Mark step complete' : 'Close out work order'),
        ),
      ),
    );
  }
}
