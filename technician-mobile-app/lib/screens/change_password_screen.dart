import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';

class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _currentController = TextEditingController();
  final _newController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _currentController.dispose();
    _newController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _error = null;
      _submitting = true;
    });
    if (_newController.text != _confirmController.text) {
      setState(() {
        _error = 'New passwords do not match.';
        _submitting = false;
      });
      return;
    }
    final changed = await context.read<AppController>().changePassword(
          _currentController.text,
          _newController.text,
        );
    if (!mounted) return;
    if (!changed) {
      setState(() {
        _error = context.read<AppController>().lastError ?? 'Password change failed.';
        _submitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Change password')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Set a new password', style: theme.textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text('Use at least 8 characters.', style: theme.textTheme.bodyMedium),
            const SizedBox(height: 28),
            TextField(controller: _currentController, obscureText: true, decoration: const InputDecoration(labelText: 'Current password')),
            const SizedBox(height: 16),
            TextField(controller: _newController, obscureText: true, decoration: const InputDecoration(labelText: 'New password')),
            const SizedBox(height: 16),
            TextField(controller: _confirmController, obscureText: true, decoration: const InputDecoration(labelText: 'Confirm new password')),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: TextStyle(color: theme.colorScheme.error), key: const Key('change-password-error')),
            ],
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submitting ? null : _submit,
                child: _submitting ? const CircularProgressIndicator() : const Text('Update password'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}