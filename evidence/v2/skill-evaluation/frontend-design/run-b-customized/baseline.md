# Fleet overview design task

Starting revision `700fc22a8f546b5159056242d95d85b6f0ba4388`.

- Reference `frontend-design-sample/fleet.png`, SHA-256 `5346646f61e7fed370a335cb0d6fc98e7d6a9dc989992aace2d33f0e3289903c`. The three adjacent concepts inform visual consistency.
- Original skill `skills/frontend-design/SKILL.md`, SHA-256 `d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3`. Local Git blob `a5333457c414d20d625f307df945842c0952ecc3` matches the GitHub Contents API response for the pinned revision. [Anthropic upstream](https://github.com/anthropics/skills/blob/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/frontend-design/SKILL.md)
- Agent platform Codex. Exact model variant, inference settings and token usage unavailable.

## Frozen checklist

1. Compare desktop and narrow captures with the fleet reference. Use horizontal navigation, a compact counts strip and roster, grouped selected-vehicle panels, an off-white canvas and muted semantic accents.
2. Match API counts and the three registered V2 identities. Show selected health, availability, faults, recovery, source silence, LiDAR and observation metadata as supplied. Provide vehicle and diagnostics destinations. Preserve V1 defaults and existing API behavior.
3. Verify available, stale, unavailable and recovering states. Label retained observations last known and synthetic previews visibly. Show honest empty states for missing observations and action history. Keep execution and observed recovery independent.
4. Switch vehicles while replies are delayed and verify observations and actions stay with their vehicle.
5. Check readable narrow layout, visible keyboard focus, keyboard selection and textual status labels.

Run A uses the unchanged original frontend-design skill. Reuse this task and baseline, the same reference and fixtures, and the exact checks recorded with the verification in a fresh session for Run B.

## Run B setup

- Starting frontend, fixtures and reference matched Run A's frozen checkpoint `ea409dc` via `git diff --exit-code 700fc22 ea409dc -- frontend tests/fixtures/v2 frontend-design-sample/fleet.png` (exit 0).
- The unchanged common browser harness comes from `ca1cdb4ab6d6bd2f12144ba1d5b382b0a640bd2b`. It uses synthetic HTTP routes and 1100 × 850 and 390 × 844 viewports.
- Customized SDV Frontend Design version 1.0.0 from main `7c5db37f601e49a58f9281f88e730e0d279fb25d`.
- Codex, Node v24.18.0, Google Chrome 157.0.8103.50. Exact inference settings and token usage are unavailable. Baseline setup observed at 2026-11-26 13:16:49 -05:00.
- Compare initial-to-initial and final-to-final for visual similarity, data correctness, responsive layout, accessibility, defects, rework, reuse, elapsed time, observable tokens and verification coverage.

## Design plan and field mapping

Use a horizontal navigation bar, compact count band and six-column roster above a split board. Put selection, status and destinations on the left. Group front LiDAR, action execution and recovery on the right, with observation identity and clocks below. Stack panels on small screens and reflow roster rows with their own field labels. Use shared typography, cards and controls with Fleet-scoped off-white, sage, amber, rose, powder blue and lavender surfaces.

| Operator question | Contract and treatment |
| --- | --- |
| Which vehicles are registered and currently healthy? | Registry IDs and fleet counters are independent of the selected snapshot. Only available vehicles contribute to health totals. Roster fields come from the fleet snapshot and retained data is labelled last known. |
| What does the selected vehicle report? | Selected state supplies health, availability, active faults and front LiDAR in metres. Missing and invalid readings stay unknown. Keep observation provenance separate from preview mode and preserve valid zero. |
| Did the command execute and did health recover? | Action record and history supply execution outcome. The selected snapshot supplies recovery state, start time and source silence, independently. |
| Which observation am I seeing? | Show event, source timestamp, session, generation, sequence and frame when supplied. Compute source age at the fleet evaluation time. Keep fleet and selected evaluation timestamps distinct. |

Plan review removed the concept's unsupported speed, battery, coolant and tire tiles. Keep the existing select and refresh sequence, use current navigation destinations, and preserve polling, command enablement and request isolation in the model. A static roster avoids replacing focused controls during polling.
91caaba0074b467c0e64f5f2171d3d0b2d2dbb87a4cfc0216224454b639f86d5  skills/sdv-frontend-design/SKILL.md
9754de470f93ecd83a1fc8123aaa044204af5e197e394eb8f2e5fa37b84717a0  frontend/tests/v2-fleet-browser.mjs
