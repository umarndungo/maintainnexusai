import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';

class CloseOutScreen extends StatefulWidget {
  const CloseOutScreen({super.key, required this.workOrderId});

  final String workOrderId;

  @override
  State<CloseOutScreen> createState() => _CloseOutScreenState();
}

class _CloseOutScreenState extends State<CloseOutScreen> {
  late final TextEditingController _partsController;
  late final TextEditingController _notesController;
  bool _photoAttached = false;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    final wo = context.read<AppController>().byId(widget.workOrderId);
    _partsController = TextEditingController(text: wo.partsUsed.isNotEmpty ? '${wo.partsUsed.first} ×1' : '');
    _notesController = TextEditingController();
  }

  @override
  void dispose() {
    _partsController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _submitting = true);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;
    context.read<AppController>().submitCloseOut(
          widget.workOrderId,
          parts: _partsController.text.trim().isEmpty ? [] : [_partsController.text.trim()],
          notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
          photoAttached: _photoAttached,
        );
    if (!mounted) return;
    Navigator.of(context).popUntil((route) => route.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: Text('Close out ${widget.workOrderId}')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('PARTS USED', style: theme.textTheme.labelSmall),
              const SizedBox(height: 8),
              TextField(controller: _partsController),
              const SizedBox(height: 20),
              Text('NOTES', style: theme.textTheme.labelSmall),
              const SizedBox(height: 8),
              TextField(
                controller: _notesController,
                minLines: 4,
                maxLines: 6,
                decoration: const InputDecoration(hintText: 'Describe the fault found and the repair performed…'),
              ),
              const SizedBox(height: 20),
              Text('PHOTO EVIDENCE', style: theme.textTheme.labelSmall),
              const SizedBox(height: 8),
              InkWell(
                onTap: () => setState(() => _photoAttached = !_photoAttached),
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  width: double.infinity,
                  height: 96,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: theme.cardColor,
                    border: Border.all(color: theme.dividerColor, style: BorderStyle.solid),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: _photoAttached
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.check_circle_rounded, size: 18, color: theme.colorScheme.secondary),
                            const SizedBox(width: 8),
                            const Text('completed-work.jpg attached'),
                          ],
                        )
                      : Text('+ Add photo of completed work', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.55))),
                ),
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: ElevatedButton(
          onPressed: _submitting ? null : _submit,
          child: _submitting
              ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white))
              : const Text('Submit & close work order'),
        ),
      ),
    );
  }
}
