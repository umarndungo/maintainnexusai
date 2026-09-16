import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_controller.dart';
import '../widgets/mono_text.dart';
import 'notification_preview_screen.dart';
import 'sync_conflict_screen.dart';
import 'change_password_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppController>();
    final theme = Theme.of(context);

    return SafeArea(
      bottom: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 140),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Settings', style: theme.textTheme.headlineSmall),
            const SizedBox(height: 20),
            _ProfileCard(employeeId: app.employeeId),
            const SizedBox(height: 28),
            _SettingsCard(
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.lock_reset_rounded),
                title: const Text('Change password'),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ChangePasswordScreen())),
              ),
            ),
            const SizedBox(height: 28),
            Text('APPEARANCE', style: theme.textTheme.labelSmall),
            const SizedBox(height: 10),
            _SettingsCard(
              child: Column(
                children: [
                  _ThemeOption(
                    label: 'System',
                    icon: Icons.brightness_auto_rounded,
                    selected: app.themeMode == ThemeMode.system,
                    onTap: () => app.setThemeMode(ThemeMode.system),
                  ),
                  Divider(color: theme.dividerColor, height: 1),
                  _ThemeOption(
                    label: 'Light',
                    icon: Icons.light_mode_rounded,
                    selected: app.themeMode == ThemeMode.light,
                    onTap: () => app.setThemeMode(ThemeMode.light),
                  ),
                  Divider(color: theme.dividerColor, height: 1),
                  _ThemeOption(
                    label: 'Dark',
                    icon: Icons.dark_mode_rounded,
                    selected: app.themeMode == ThemeMode.dark,
                    onTap: () => app.setThemeMode(ThemeMode.dark),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            Text('DEMO CONTROLS', style: theme.textTheme.labelSmall),
            const SizedBox(height: 4),
            Text(
              'This build has no live backend — these simulate the conditions the offline-first design handles (spec, Part 1 · Mobile · 03–04).',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 10),
            _SettingsCard(
              child: Column(
                children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Simulate offline'),
                    subtitle: Text(app.isOnline ? 'Connected' : 'No connection', style: theme.textTheme.bodySmall),
                    value: !app.isOnline,
                    onChanged: (offline) => app.setOnline(!offline),
                  ),
                  Divider(color: theme.dividerColor, height: 1),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Simulate sync conflict'),
                    subtitle: const Text('Shows Mockup 7 for the first work order'),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () {
                      app.simulateSyncConflict();
                      Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SyncConflictScreen()));
                    },
                  ),
                  Divider(color: theme.dividerColor, height: 1),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Preview SMS fallback notification'),
                    subtitle: const Text('Shows Mockup 8, the lock-screen deep link'),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const NotificationPreviewScreen())),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: app.signOut,
                child: const Text('Sign out'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileCard extends StatelessWidget {
  const _ProfileCard({required this.employeeId});

  final String employeeId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.dividerColor),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 22,
            backgroundColor: theme.colorScheme.secondary.withValues(alpha: 0.2),
            child: Text(
              employeeId.isEmpty ? '?' : employeeId.substring(0, 1),
              style: TextStyle(color: theme.colorScheme.secondary, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Technician', style: theme.textTheme.titleMedium),
                const SizedBox(height: 2),
                MonoText(employeeId.isEmpty ? '—' : '$employeeId · STN-B', fontSize: 12, color: theme.colorScheme.onSurface.withValues(alpha: 0.55)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  const _SettingsCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      decoration: BoxDecoration(
        color: theme.cardColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: theme.dividerColor),
      ),
      // ListTile/SwitchListTile paint their ink splashes on the nearest
      // Material ancestor — without this, the surrounding colored
      // Container above hides that ink entirely.
      child: Material(type: MaterialType.transparency, child: child),
    );
  }
}

class _ThemeOption extends StatelessWidget {
  const _ThemeOption({required this.label, required this.icon, required this.selected, required this.onTap});

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(icon, size: 20),
      title: Text(label),
      trailing: selected ? Icon(Icons.check_rounded, color: theme.colorScheme.secondary) : null,
      onTap: onTap,
    );
  }
}
