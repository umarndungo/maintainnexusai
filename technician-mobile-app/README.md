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

## SMS deep link (Build Plan Phase 2 step 5)

A dispatch SMS carries `maintainnexus://work-orders/{id}` — tapping it
opens the app straight to that work order's detail screen, cold-start
or warm-start. This is the "push notification opens straight to the
work order" outcome from the spec, delivered via SMS instead of FCM:
distribution is enterprise/sideload (Build Plan Phase 0), and there's
no Firebase project yet, so `integrations/fcm_client.py` on the
backend stays wired but inert while this ships tonight.

- `lib/services/deep_link_service.dart` — listens via `app_links` for
  both the cold-start initial link and any warm-start link tap.
- `android/app/src/main/AndroidManifest.xml` — `maintainnexus://`
  intent-filter (custom scheme, not an `https://` App Link — needs no
  domain ownership/verification, which matters for sideload).
- `ios/Runner/Info.plist` — matching `CFBundleURLTypes` entry.
- If the linked work order isn't cached locally yet (this build has no
  live API sync — see below), `DeepLinkNotFoundScreen` says so plainly
  instead of crashing; `AppController.tryById` is the null-safe lookup
  behind it.
- Manual test: `adb shell am start -a android.intent.action.VIEW -d "maintainnexus://work-orders/WO-3391"`
  (with the app installed) opens straight to that work order if it's
  in `lib/data/mock_data.dart`, or the not-found screen otherwise.

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
