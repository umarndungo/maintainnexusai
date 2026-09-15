import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// The synced/offline badge that "sits in the same place on every
/// screen" (spec, "Principles": "Connectivity state is always visible,
/// never hidden").
class ConnectivityBadge extends StatelessWidget {
  const ConnectivityBadge({super.key, required this.isOnline, this.syncing = false});

  final bool isOnline;
  final bool syncing;

  @override
  Widget build(BuildContext context) {
    final Color color = syncing
        ? AppColors.offlineAmber
        : isOnline
            ? AppColors.onlineGreen
            : AppColors.offlineAmber;
    final String label = syncing ? 'SYNCING' : (isOnline ? 'SYNCED' : 'OFFLINE');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _Dot(color: color, pulsing: syncing),
          const SizedBox(width: 6),
          Text(label, style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color)),
        ],
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  const _Dot({required this.color, required this.pulsing});

  final Color color;
  final bool pulsing;

  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  // Created eagerly in initState (not as a lazy `late final` field) so the
  // ticker's vsync lookup always runs while the element is still active —
  // a lazy initializer only run from dispose() (when `pulsing` is never
  // true) tries that lookup after the element has been deactivated.
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(milliseconds: 700))..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.pulsing) {
      return Container(width: 7, height: 7, decoration: BoxDecoration(color: widget.color, shape: BoxShape.circle));
    }
    return FadeTransition(
      opacity: _controller.drive(CurveTween(curve: Curves.easeInOut)),
      child: Container(width: 7, height: 7, decoration: BoxDecoration(color: widget.color, shape: BoxShape.circle)),
    );
  }
}
