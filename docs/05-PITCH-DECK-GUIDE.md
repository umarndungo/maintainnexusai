# Pitch Deck Implementation Guide

**Owner:** Pitch deck owner
**Reads:** `00-PROJECT-DOC.md` §1, §6 before starting.

---

## 1. Scope

The notes specify: real-time info flow → framed as cost/downtime savings for a non-technical audience.
This deck's job is to make the executive dashboard's numbers land as a story, not to re-explain the
architecture.

## 2. Narrative spine

1. **The problem** — unplanned downtime on loading arms/pumps/valves is expensive and, more importantly
   for this audience, a safety risk when equipment fails without warning under increased throughput.
2. **The shift** — reactive maintenance → condition-based maintenance, triggered by real sensor data,
   not a calendar.
3. **How it works, at a glance** — one simplified version of the flow diagram in the project doc §2:
   sensor → risk score → engineer approval → technician dispatch → closed loop. Don't put the full
   lifecycle state machine on a slide; that's an engineering artifact, not a pitch artifact.
4. **What it prevents** — this is where the executive-dashboard numbers go: downtime avoided, cost
   saved, uptime trend. These should be *the actual numbers the backend computes*, not placeholder
   figures — coordinate with Backend/Frontend for a live or near-live pull once the executive-summary
   endpoint exists, rather than hand-typing numbers that will drift from the real dashboard.
5. **Why now** — automation/throughput is increasing; this is the system that keeps that safe.
6. **Trust/compliance, one line** — every maintenance decision is logged in a tamper-evident record
   (`07-AUDITING-GUIDE.md`). This is worth a single reassuring line for a safety-conscious or
   compliance-minded audience, not a slide of its own — "who approved what, when, and it can't be
   quietly edited afterward" is the whole pitch; the hash-chain mechanics stay in the engineering docs.

## 3. Tasks

- Draft slide-by-slide outline following the spine above; keep it to what a non-technical stakeholder
  needs, not an engineering walkthrough.
- Once `/api/v1/dashboard/executive-summary` exists (Backend guide §2 step 7), pull real or realistic
  demo numbers from it rather than inventing figures — even a staging-environment number is more
  credible than a made-up one, and it stays consistent with what the actual dashboard will show
  investors/stakeholders if they ask to see it live.
- Build one simplified flow visual (not the full state machine) for the "how it works" slide.
- Coordinate with Frontend on whether the executive dashboard itself can be demoed live instead of
  screenshotted, if timing allows — a live demo is stronger than static slides for this kind of pitch.

## 4. AI context block

```
I'm building the pitch deck for MaintainNexus, a predictive-maintenance system for depot equipment
(loading arms, pumps, valves) that shifts from reactive to condition-based maintenance using sensor
telemetry and a risk-scoring model, with an engineer-approval step before any technician is dispatched.

What I need help with: a slide narrative for a non-technical audience (problem → shift to
condition-based maintenance → simplified how-it-works → downtime/cost impact → why this matters
given increasing automation and throughput). I should use real or realistic numbers from the
system's own executive-summary dashboard endpoint rather than inventing figures, and keep the
architecture slide simplified — no full state machines or API contracts, those belong in the
engineering docs, not the pitch.
```
