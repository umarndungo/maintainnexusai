import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';
import '../widgets/mono_text.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key});

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _idController = TextEditingController(text: 'TC-1042');
  final _passcodeController = TextEditingController(text: '••••••');
  bool _submitting = false;

  @override
  void dispose() {
    _idController.dispose();
    _passcodeController.dispose();
    super.dispose();
  }

  Future<void> _signIn() async {
    setState(() => _submitting = true);
    await Future<void>.delayed(const Duration(milliseconds: 450));
    if (!mounted) return;
    context.read<AppController>().signIn(_idController.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // A plain scrollable column, not Spacer-based layout — this keeps
    // the sign-in form safe on short viewports (small phones, split
    // screen, this project's own widget tests) without special-casing.
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 40, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44,
                height: 44,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: theme.colorScheme.secondary,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'M',
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: 20, color: Colors.black),
                ),
              ),
              const SizedBox(height: 40),
              Text('Sign in', style: theme.textTheme.displaySmall),
              const SizedBox(height: 6),
              Text(
                'Depot 4 — Technician access',
                style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.6)),
              ),
              const SizedBox(height: 32),
              Text('EMPLOYEE ID', style: theme.textTheme.labelSmall),
              const SizedBox(height: 8),
              TextField(controller: _idController, style: theme.textTheme.bodyLarge),
              const SizedBox(height: 20),
              Text('PASSCODE', style: theme.textTheme.labelSmall),
              const SizedBox(height: 8),
              TextField(controller: _passcodeController, obscureText: true, style: theme.textTheme.bodyLarge),
              const SizedBox(height: 16),
              Center(
                child: TextButton.icon(
                  onPressed: _signIn,
                  icon: const Icon(Icons.fingerprint_rounded, size: 18),
                  label: const Text('Use biometric sign-in'),
                ),
              ),
              const SizedBox(height: 56),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_rounded, size: 16, color: theme.colorScheme.secondary),
                  const SizedBox(width: 6),
                  Text('Demo access is ready', style: theme.textTheme.bodySmall),
                ],
              ),
              const SizedBox(height: 4),
              Center(
                child: Text(
                  'Demo user IDs are prefilled. Sign-in uses local\nmock state; passcode is not verified in this build.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall,
                ),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _submitting ? null : _signIn,
                  child: _submitting
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
                        )
                      : const Text('Sign in'),
                ),
              ),
              const SizedBox(height: 8),
              Center(child: MonoText('TC-1042 · STN-B', fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.4))),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
