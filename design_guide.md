# Design System — Community

A reference guide distilled from the design-system artboards in this folder (Colors, Typography, Font, Shadow, Icons, and all component specs). Use it as the single source of truth for foundations and component behavior when implementing UI.

---

## Table of Contents

1. [Foundations](#foundations)
   - [Color](#color)
   - [Typography](#typography)
   - [Font](#font)
   - [Elevation / Shadow](#elevation--shadow)
   - [Iconography](#iconography)
2. [Components](#components)
   - [Button](#button)
   - [Button Group](#button-group)
   - [Badge & Chip](#badge--chip)
   - [Input](#input)
   - [Dropdown](#dropdown)
   - [Checkbox](#checkbox)
   - [Radio](#radio)
   - [Toggle](#toggle)
   - [Stepper](#stepper)
   - [Alert](#alert)
   - [Card](#card)
   - [Tab](#tab)
   - [Navbar: Top](#navbar-top)
   - [Navbar: Bottom](#navbar-bottom)
   - [List](#list)
   - [Page Control](#page-control)
   - [Pagination](#pagination)
   - [Pop-Up](#pop-up)
   - [Action Sheet](#action-sheet)
   - [Context Menu](#context-menu)
   - [Tooltip](#tooltip)
   - [Breadcrumbs](#breadcrumbs)
   - [Avatar](#avatar)
   - [Loader](#loader)
   - [Progress Bar](#progress-bar)

---

## Foundations

### Color

Every hue is expressed as a 10-step ramp (**900 → 50**, darkest to lightest), plus **Black** and **White** expressed as an alpha ramp (100% → 10%) for use as overlays/scrims. Hex values below were sampled directly from the source swatches.

#### Black (alpha ramp)

| Alpha | Hex |
|---|---|
| 100% | `#000000` |
| 90% | `#1A1A1A` |
| 80% | `#333333` |
| 70% | `#4D4D4D` |
| 60% | `#666666` |
| 50% | `#808080` |
| 40% | `#999999` |
| 30% | `#B3B3B3` |
| 20% | `#CCCCCC` |
| 10% | `#E6E6E6` |

#### White (alpha ramp)
`#FFFFFF` at every step — apply opacity in-code (100%→10%) rather than baked-in hex, since white-on-white has no visible tint.

#### Primary (indigo / blue-violet) — brand color

| Step | Hex |
|---|---|
| 900 | `#212967` |
| 800 | `#2B3587` |
| 700 | `#3745AF` |
| 600 | `#4758E0` |
| 500 | `#4E61F6` |
| 400 | `#7181F8` |
| 300 | `#8895F9` |
| 200 | `#AEB6FB` |
| 100 | `#C8CEFC` |
| 50 | `#EDEFFE` |

500 is the base/interactive brand color; 800/900 are used for hover/press states; 50–200 are used for tints, subtle fills, and focus backgrounds.

#### Grey (neutrals — text, borders, surfaces)

| Step | Hex |
|---|---|
| 900 | `#131927` |
| 800 | `#212936` |
| 700 | `#394050` |
| 600 | `#4D5461` |
| 500 | `#6D717F` |
| 400 | `#9EA2AE` |
| 300 | `#D2D5DB` |
| 200 | `#E5E7EA` |
| 100 | `#F3F4F6` |
| 50 | `#F9FAFB` |

900 doubles as the default heading/body text color; 100/50 are page and card backgrounds; 300/400 are borders and disabled content.

#### Green / Success

| Step | Hex |
|---|---|
| 900 | `#1C4D27` |
| 800 | `#256533` |
| 700 | `#308242` |
| 600 | `#3DA755` |
| 500 | `#43B75D` |
| 400 | `#69C57D` |
| 300 | `#81CF92` |
| 200 | `#A9DEB4` |
| 100 | `#C5E9CD` |
| 50 | `#ECF8EF` |

#### Red / Danger

| Step | Hex |
|---|---|
| 900 | `#641D1A` |
| 800 | `#832523` |
| 700 | `#A9302D` |
| 600 | `#D93E39` |
| 500 | `#EE443F` |
| 400 | `#F16965` |
| 300 | `#F4827E` |
| 200 | `#F7A9A7` |
| 100 | `#FAC5C3` |
| 50 | `#FDECEC` |

#### Yellow / Warning

| Step | Hex |
|---|---|
| 900 | `#6B4700` |
| 800 | `#8C5E00` |
| 700 | `#B57900` |
| 600 | `#E89B00` |
| 500 | `#FFAA00` |
| 400 | `#FFBB33` |
| 300 | `#FFC654` |
| 200 | `#FFD88A` |
| 100 | `#FFE5B0` |
| 50 | `#FFF7E6` |

#### Blue / Info

| Step | Hex |
|---|---|
| 900 | `#003F6B` |
| 800 | `#00528C` |
| 700 | `#006AB5` |
| 600 | `#0088E8` |
| 500 | `#0095FF` |
| 400 | `#33AAFF` |
| 300 | `#54B8FF` |
| 200 | `#8ACEFF` |
| 100 | `#B0DEFF` |
| 50 | `#E6F4FF` |

**Usage pattern across components:** the 500/600 step is the "solid/filled" tone, 50/100 is the "soft/tinted" background pairing with the 500–700 step as its text/icon/border color, and 700–900 are reserved for hover and pressed states of solid surfaces.

---

### Typography

Typeface: **Inter** (see [Font](#font)). All styles use `0` letter-spacing.

#### Text styles

| Style | Weight | Size | Line height |
|---|---|---|---|
| H1. Headline | Semi Bold | 48 | 58 |
| H2. Headline | Semi Bold | 40 | 48 |
| H3. Headline | Semi Bold | 32 | 38 |
| H4. Headline | Semi Bold | 28 | 34 |
| H5. Headline | Semi Bold | 24 | 28 |
| S1. Subtitle | Semi Bold | 18 | 28 |
| S2. Subtitle | Semi Bold | 16 | 24 |
| B1. Body | Regular | 16 | 24 |
| B2. Body | Medium | 16 | 24 |
| B3. Body | Regular | 14 | 20 |
| B4. Body | Medium | 14 | 20 |
| C1. Caption | Regular | 12 | 16 |
| C2. Caption | Medium | 12 | 16 |
| C3. Caption | Medium | 10 | 14 |
| Label | Medium | 12 | 16 |

#### Button text styles

| Style | Weight | Size | Line height |
|---|---|---|---|
| Giant | Semi Bold | 18 | 24 |
| Large | Semi Bold | 16 | 20 |
| Medium | Semi Bold | 14 | 16 |
| Small | Semi Bold | 12 | 16 |
| Tiny | Semi Bold | 10 | 12 |

---

### Font

**Inter** — a variable font family designed for screens, with a tall x-height for readability in mixed/lower case, contextual alternates, slashed zero, and tabular figures.

- Project: [github.com/rsms/inter](https://github.com/rsms/inter)
- Led by Rasmus Andersson.
- Use the variable weight axis (or the closest static cuts — Regular / Medium / Semi Bold) to hit the weights specified in [Typography](#typography).

---

### Elevation / Shadow

An 8-step elevation scale, **100 (subtlest) → 800 (deepest)**. Shadows are soft, neutral (grey/black-based), and increase in blur/spread/offset as the step number increases — used to lift cards, menus, pop-ups, and dropdown panels off the page in that order. As a rule of thumb:

| Step | Suggested use |
|---|---|
| 100–200 | Resting cards, list rows, inputs |
| 300–400 | Raised cards, hover states |
| 500–600 | Dropdowns, popovers, context menus |
| 700–800 | Modals, pop-ups, action sheets |

---

### Iconography

**Library:** [Iconoir](https://iconoir.com) ([Figma resource](https://www.figma.com)) — free, no premium tier or sign-up, available as SVG, Font, React, React Native, Flutter, Figma, and Framer packages.

Style: outlined/stroke icons, consistent stroke weight, on a square grid.

Category set included in the library (used to organize the icon picker):

Navigation, Design Tools, Actions, Music, System, Activities, Photos and Videos, Maps, Communication, Transport, Home, Layout, Security, Devices, Finance, Identity, Science, Docs, Animations, Nature, Other, Editor, Connectivity, Development, Gaming, Shopping, Weather, Cloud, Emojis, Clothing, Shapes, Git, 3D Editor, Database, Users, Buildings, Social, Gestures, Audio, Organization, Food, Health, Analytics, Business, Tools, Animals.

---

## Components

Unless noted, components are documented across the same state machine: **Default → Hover → Focus → Press/Selected → Disabled**, and (where applicable) semantic variants: **Default (Primary) / Success / Info / Warning / Error**.

### Button

**Sizes:** Giant, Large, Medium, Small, Tiny (button text styles map 1:1, see [Typography](#typography)).

**Variants:**
1. **Solid (Filled)** — Primary-500 background, white label; Hover → Primary-800; Press → Primary-900; Disabled → Grey-100/300 (muted fill, muted label).
2. **Outline** — 1–2px Primary-500 border, transparent fill, Primary-600 label; Hover → Primary-50 fill; Focus → visible ring border; Press → Primary-100 fill; Disabled → grey border/label.
3. **Ghost / Text** — no border or fill, Primary-600 label; Hover/Press → Primary-50/100 tinted background; Disabled → grey label.

**Anatomy:** optional leading icon, label, optional trailing icon (arrow shown in spec is a placeholder slot); icon-only square variant available at every size.

**States per variant:** Default, Hover, Focus, Press, Disabled — see states table pattern above. Focus state adds a visible outer ring in Primary-300/400.

### Button Group

- **Segmented row** of buttons sharing one continuous border, in Giant / Large / Medium sizes.
- States: Default, Hover, Focus, Press, **Selected** (solid Primary-500 fill on the active segment while siblings stay outlined), Disabled.
- Supports 2–5 segments, label-only or label+icon segments, and an **icon-only segmented control** (e.g. back / up / forward).
- Works with both Outline and Solid base styles; a mixed group (one solid "primary action" segment + outline siblings) is a supported pattern.

### Badge & Chip

**Sizes:** Medium, Small, Tiny.

**Semantic colors:** Default (Primary), Success (Green), Info (Blue), Warning (Yellow), Error (Red).

**Fill styles per color:**
- **Solid** — colored-500 background, white text/icon.
- **Soft (tinted)** — colored-50 background, colored-600/700 border & text.
- **Outline** — transparent background, colored border, colored text.

**Anatomy:** optional leading icon (star placeholder), label, optional trailing dismiss `×` (chip behavior) — icon-only round badge variant also included. "Button" labeled variant shows a badge used as a compact action pill.

### Input

**Sizes:** Large, Medium. Each field = Label + control (leading icon slot + placeholder/value + trailing chevron/icon) + helper text below.

**States:**
| State | Border | Fill | Helper text |
|---|---|---|---|
| Default | Grey-300 | White | Grey helper |
| Filled | Grey-300 | White (value present) | Grey helper |
| Hover | Grey-400 | Grey-50 | Grey helper |
| Focus | Primary-500 (2px) | White | Primary helper |
| Disabled | Grey-200 | Grey-50 | Grey (muted) |
| Success | Green-500 border | Green-50 tint | Green "Success Text" |
| Info | Blue-500 border | Blue-50 tint | Blue "Info Text" |
| Warning | Yellow-500 border | Yellow-50 tint | Yellow "Warning Text" |
| Error | Red-500 border | Red-50 tint | Red "Error Text" |

Validation states restyle the border, background tint, and helper-text color together as one unit.

### Dropdown

- **Trigger** = Input-style control with leading icon + value/placeholder + chevron that flips on expand. States: Default, Hover, Expanded (open, border highlighted), Disabled.
- **Menu/Option list**: options in Default, Hover (Grey-50/100 row highlight), Selected (checkbox checked / checkmark, Primary-500), Disabled.
- Supports **single-select** (checkmark, closes on pick), **multi-select with checkboxes** (stays open, trigger shows "Selected: N options"), and a **borderless list variant** (checkmarks only, no checkbox control) for compact multi-select menus.

### Checkbox

**States:** Default, Hover, Focus (ring), Selected (checked — Primary-500 fill, white check), **Indeterminate** (Primary-500 fill, white dash), Disabled.
Square control, ~2px rounded corners; used bare or paired with a "Placeholder" label on either side (label-left or label-right layouts supported).

### Radio

**States:** Default, Hover, Focus (ring), Selected (Primary-500 outer ring + filled center dot), Disabled.
Circular control; same label-left / label-right / bare layouts as Checkbox.

### Toggle

**States:** Default (off = Grey track; on = Primary-500 track, white knob), Hover (darker track shade), Focus (ring around track), Disabled (faded track/knob).
Shown bare and paired with a "Placeholder" label on either side.

### Stepper

Pill-shaped **− / +** control split by a center divider. Two visual weights:
- **Tinted** — Primary-50 background, Primary-600 icons/divider.
- **Outline** — white background, Grey border, dark icons.

Used standalone or inline in a List row/quantity field.

### Alert

**Semantic variants:** Default (Primary), Success, Info, Warning, Error.
**Fill styles:** Solid (colored-500/600 background, white icon/title/body, white or translucent-white action links) and Soft (colored-50 background, colored-600/700 icon/title, colored text actions, grey secondary action).

**Anatomy:** leading icon, bold Title, supporting body copy, and one or two inline text-button actions along the bottom edge. A minimal variant (actions only, no icon/title/body) is also supported for compact inline confirmations.

### Card

**Layouts:**
- **Horizontal – Small**: fixed-size image/thumbnail on the left, Title + description on the right, no actions.
- **Vertical**: full-width image on top (rounded top corners), Title + description below, followed by a stacked Solid button and an Outline button.

**Composable slots** (per Examples): image is optional, Title is optional (description can lead alone), and action buttons range from zero to two (solid primary always above outline secondary when both are present).

### Tab

**States:** Default (outline pill, Primary-600 text/icon), Hover (Primary-50 tint), Focus (ring), Selected (solid Primary-500 fill, white text/icon), Disabled (grey, no border).

**Anatomy:** optional leading icon, label, optional trailing icon — icons can be omitted, leading-only, trailing-only, or both.

Used as a horizontal row of pill tabs where exactly one tab is Selected and the rest sit in their Default (or Disabled) state.

### Navbar: Top

**Anatomy slots:** leading zone (back chevron + Label, or up to 3 icon actions), center zone (Title, optionally with a Secondary Text subtitle beneath), trailing zone (up to 3 icon actions, or a single trailing Label + chevron).

**Compositions supported:** icon-only leading/trailing clusters; Title-only centered; Title + secondary text; Label back-link + Title + icon action(s); Label back-link + Title + trailing Label; any leading/trailing slot can carry 1–3 icons or 1 label.

### Navbar: Bottom

**Layout:** a top accent/indicator bar (short highlight above the active item) sits above a row of 2–5 evenly-spaced tab items.

**Item anatomy:** icon (+ optional text label beneath). Active item = Primary-500 icon/label + indicator bar segment above it; inactive items = Grey/outline icon, no label color emphasis (label optional per item — icon-only bottom nav is supported).

**Item counts:** 2, 3, 4, or 5 items per bar, with the active-indicator bar width matching the active item's column.

### List

**Row anatomy (composable):** leading slot (icon, avatar, or nothing) + Title (+ optional secondary line) + trailing slot.

**Trailing slot variants:** none, chevron only, "Details" label + chevron, numeric/notification badge (+ optional chevron), Toggle, Radio, Checkbox, Stepper (− / +).

**Row states:** rows sit on a subtle Grey-50 stripe background by default; selected/active states follow the trailing control's own state (checked checkbox, on toggle, filled radio, badge count).

Common presets: plain title list, title+details list, title+chevron list, avatar list, icon list, toggle list, checkbox list, radio list, and counter/notification list.

### Page Control

Row of dots indicating pagination position in a carousel/onboarding flow — one dot is Primary-500 (active/current), the rest are Primary-100/200 (inactive), with dot size and count truncation:
- **Horizontal**: 3–8 dots in a row; when the count exceeds a threshold, trailing dots shrink (fish-eye/telescoping effect) to indicate "more pages" without listing every dot at full size.
- **Vertical**: same shrink logic applied top-to-bottom.

### Pagination

**Elements:** numbered page pill (circular) and directional chevron pill (‹ / ›).

**States:** Default (Primary-600 text/icon, no fill), Hover (Primary-50 fill), Focus (ring border), Selected (solid Primary-500 fill, white text), Disabled (grey, muted).

**Composition example:** `‹  1  [2]  3  4  ›` — previous/next chevrons flank numbered pills; the current page is the only Selected/solid pill.

### Pop-Up

Centered modal dialog. **Anatomy (all optional/composable):** Title, body copy, an input field, and one or two stacked/inline action buttons (Solid primary + Outline secondary).

**Supported compositions:** Title+body+2 buttons; Title+body+input+2 buttons; body-only+2 buttons; Title+1 button only; Title+body+input+2 buttons stacked vertically; any subset of Title/body/input can be dropped while keeping the action button(s).

Container: rounded corners on a Grey-50/white surface, elevated with a Shadow step (see [Elevation](#elevation--shadow)).

### Action Sheet

Bottom-sheet style stacked menu. **Anatomy:** optional header (Title + supporting body text), a list of full-width "Action" rows (Primary-600 text, row dividers), and a separated **Cancel** button (Solid Primary-500) below.

**Row variants:** 2–5 action rows; a destructive action can be styled Red-500 within the same list (see Examples: one row shown in red for a delete/destructive action). Header can be title+body, body-only, or omitted entirely (actions + Cancel only).

### Context Menu

Compact floating menu, typically triggered from a **⋯** (more) round icon button.

**Row anatomy:** leading icon + label, or label + trailing icon (icon side is flexible). A destructive row (e.g. "Delete") is styled in Red-500 with a matching red icon and is conventionally placed last, separated from neutral rows.

**States:** Default row, Hover/Press (Grey-50/Primary-50 row highlight). Menus range from 3–5 rows and float on a white surface with rounded corners and shadow elevation.

### Tooltip

Solid Primary-500 fill, white label text, rounded pill/rectangle body with a directional pointer/nub.

**Placements:** Bottom (pointer on top edge), Top (pointer on bottom edge), Left (pointer on right edge), Right (pointer on left edge) — the tooltip body is positioned opposite its pointer, i.e. a "Bottom" tooltip sits below its anchor with the pointer aimed up at the anchor.

### Breadcrumbs

Horizontal trail of items separated by chevrons (`>`).

**Item states:** Default (Grey/outline icon+text), Hover (Grey-50 tint), Focus (ring, Primary tint), Selected/current (bold dark text + solid icon, no chevron continuation needed after it), Disabled (faded).

**Composition:** each item can show a leading icon, trailing icon, or both; trail length ranges from 2–5 items; the current/last item is visually emphasized (bold) versus the earlier, de-emphasized ancestors.

### Avatar

**Sizes:** an 8-step scale from largest to smallest (matching the icon/badge sizing rhythm), all circular.

**Content variants:** photographic/illustrated portrait, initials-on-Primary-500-fill, and icon-on-Primary-500-fill (e.g. generic smiley/person glyph).

**Status indicator:** small circular badge (green = online/active) docked at the bottom-right edge of the avatar, present across all sizes and content variants.

### Loader

Circular indeterminate spinner, Primary-500 stroke on transparent background, drawn as a partial ring (open gap) that rotates.

**Sizes:** 5-step size scale (largest → smallest), stroke width scales down proportionally with diameter so the ring stays visually balanced at every size.

### Progress Bar

Horizontal track (Grey-100/200, fully rounded ends) with a Primary-500 filled bar indicating percentage complete.

**Two weights:** a thinner track and a slightly thicker track (pick per density of the surrounding UI).

**Value states shown:** 0% (empty/unfilled), 20%, 40%, 60%, 80%, 100% (fully filled) — percentage label sits inline at the start/end of the bar.

---

## Implementation Notes

- **Consistency rule:** every interactive component follows the same state vocabulary — Default → Hover → Focus → Press/Selected → Disabled — so a new component should be speced against that same sequence before shipping.
- **Color pairing rule:** solid = `{color}-500` fill / white content; soft = `{color}-50` fill / `{color}-600–700` content; outline = transparent fill / `{color}-500` border / `{color}-600` content. Apply this triad consistently across Button, Badge & Chip, Alert, Input, and Tab.
- **Disabled rule:** disabled content always drops to Grey-200/300 (borders/fills) and Grey-400 (text/icons), regardless of the component's semantic color.
- **Spacing/elevation:** floating surfaces (Dropdown menu, Context Menu, Pop-Up, Action Sheet, Tooltip) sit on a white/Grey-50 rounded surface with a shadow from the [Elevation](#elevation--shadow) scale — heavier elevation for modal-like surfaces (Pop-Up, Action Sheet) than for inline menus (Context Menu, Dropdown, Tooltip).
