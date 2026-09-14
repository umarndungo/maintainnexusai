import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// The high/medium/low risk chip used on work order cards and detail
/// screens. Functional color-coding per the spec — never decorative,
/// never re-themed per screen.
class RiskChip extends StatelessWidget {
  const RiskChip({super.key, required this.riskLevel});

  final String riskLevel;

  @override
  Widget build(BuildContext context) {
    final color = AppColors.riskColor(riskLevel);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Text(
        '${riskLevel.toUpperCase()} RISK',
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color, letterSpacing: 0.4),
      ),
    );
  }
}
