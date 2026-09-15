import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

class NavDestination {
  const NavDestination({required this.icon, required this.label});
  final IconData icon;
  final String label;
}

const List<NavDestination> kNavDestinations = [
  NavDestination(icon: Icons.home_rounded, label: 'Home'),
  NavDestination(icon: Icons.description_rounded, label: 'Queue'),
  NavDestination(icon: Icons.bar_chart_rounded, label: 'Insights'),
  NavDestination(icon: Icons.settings_rounded, label: 'Setting'),
];

/// The floating dark capsule bottom nav bar from the reference
/// screenshot — kept the same near-black treatment in both themes
/// (rather than flipping per-theme) so it reads as one consistent
/// piece of chrome, the way it does across the screenshot's frames.
class AppShell extends StatelessWidget {
  const AppShell({
    super.key,
    required this.currentIndex,
    required this.onDestinationSelected,
    required this.body,
  });

  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget body;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      body: body,
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(20, 0, 20, 16),
        child: Container(
          height: 64,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: const Color(0xFF14171B),
            borderRadius: BorderRadius.circular(32),
            boxShadow: [
              BoxShadow(color: Colors.black.withValues(alpha: 0.28), blurRadius: 24, offset: const Offset(0, 10)),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              for (int i = 0; i < kNavDestinations.length; i++)
                _NavItem(
                  destination: kNavDestinations[i],
                  selected: i == currentIndex,
                  onTap: () => onDestinationSelected(i),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({required this.destination, required this.selected, required this.onTap});

  final NavDestination destination;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(24),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
        padding: EdgeInsets.symmetric(horizontal: selected ? 16 : 12, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.accentOrange : Colors.transparent,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(destination.icon, size: 20, color: selected ? Colors.black : Colors.white.withValues(alpha: 0.55)),
            if (selected) ...[
              const SizedBox(width: 8),
              Text(
                destination.label,
                style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w700, fontSize: 13),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
