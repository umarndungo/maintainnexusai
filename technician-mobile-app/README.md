# MaintainNexus — Technician Mobile App

A Flutter implementation of the eight core screens from
`MaintainNexus-Mobile-Web-Spec.pdf` (Part 1 · Mobile), styled to the
design system in the reference screenshot — a light, card-and-paper
screen alongside a dark, graphite-and-amber shell — with a fully
worked dark mode added, matching the spec's own dark mockups.

## Screens implemented (spec Part 1 · Mobile · 05)

| # | Screen | File |
|---|---|---|
| 1 | Sign in | `lib/screens/sign_in_screen.dart` |
| 2 | My work orders | `lib/screens/work_orders_screen.dart` |
| 3 | Work order detail | `lib/screens/work_order_detail_screen.dart` |
| 4 | Active task (checklist) | `lib/screens/active_task_screen.dart` |
| 5 | Close out | `lib/screens/close_out_screen.dart` |
| 6 | Offline mode | `lib/screens/sync_queue_screen.dart` |
| 7 | Sync conflict | `lib/screens/sync_conflict_screen.dart` |
| 8 | SMS fallback notification | `lib/screens/notification_preview_screen.dart` |

Two extra tabs — `insights_screen.dart` and the bottom nav shell
(`widgets/app_shell.dart`) — round out the four-icon floating nav bar
from the reference screenshot (house / document / bar-chart / gear),
which isn't literally one of the eight spec screens but is the chrome
every other screen sits inside.

## Design system

- **Colors**: `lib/theme/app_colors.dart`. The dark palette is the
  spec's own tokens (Part 1 · Mobile · 01) — Graphite 800/700, Signal
  blue, and the red/amber/green risk trio. The light palette matches
  the reference screenshot's warm cream-and-white "Maintenance
  Report" screen, with near-black primary buttons. Risk and
  connectivity colors are identical in both themes — functional, not
  decorative, per the spec's principles.
- **Type**: `lib/theme/app_theme.dart`. IBM Plex Sans (via
  `google_fonts`) carries all UI text; IBM Plex Mono is reserved for
  technical data — equipment IDs, work order numbers, risk scores,
  timestamps — via the `MonoText` widget / `AppTheme.monoTextStyle`.
- **Nav bar**: `lib/widgets/app_shell.dart`. The floating dark capsule
  bar with an orange active pill from the screenshot's Home/Admin
  Panel frames — kept the same near-black treatment in both themes
  rather than flipping per-theme, so it reads as one consistent piece
  of chrome.
- **Dark mode**: toggle in Settings (System / Light / Dark), persisted
  via `shared_preferences`. Defaults to Dark on first launch.

## What's not implemented yet

This is a screens-and-design-system build, not the full app from the
spec's system architecture diagram (Part 1 · Mobile · 02). There is
**no backend, no local database, and no real background sync** —
`lib/state/app_controller.dart` is a single in-memory `ChangeNotifier`
standing in for the local store (Isar/Drift), the background sync
queue, and secure token storage shown in that diagram, seeded from
`lib/data/mock_data.dart`.

"Offline", "sync queue", and "sync conflict" are simulated from
Settings → **Demo controls**, since there's no real network or second
technician session to trigger them against. Wiring this up to the
actual FastAPI backend in this repo (`api/`, `08-MOBILE-GUIDE.md` per
the spec's reference table) is the next step.

## Running it

```bash
flutter pub get
flutter run                 # any connected device/emulator
flutter run -d chrome        # web
flutter build apk --debug    # sideload onto Android
```

`flutter analyze` and `flutter test` are both clean.
