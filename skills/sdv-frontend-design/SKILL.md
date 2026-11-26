---
name: sdv-frontend-design
description: Design and implement clear, contract-aware engineering dashboards for the QA-SDV-Project. Use for Fleet, Vehicles, Diagnostics, Performance, shared dashboard components, telemetry presentation, responsive layouts, and frontend visual or behavioral verification.
---

# SDV Frontend Design

Version 1.0.0 — customized derivative of Anthropic's frontend-design skill.

Design for an operator monitoring a fleet of software-defined vehicles. Combine deliberate visual identity with trustworthy data, clear operational states, and maintainable implementation. Preserve the original skill's emphasis on subject-specific design, typography, visual hierarchy, useful copy, restraint, and screenshot-based critique.

## 1. Establish the task and data contract

Read the repository's AGENTS.md and docs/SOURCE-OF-TRUTH.md. Follow their precedence rules. Read only the relevant sections of the current V2 plan, technical decisions, acceptance criteria and interface contracts. Inspect the existing page, styles, API client, state model and applicable fixtures before editing.

For each UI section identify:

- The operator's question or action.
- The actual API field or existing fixture that supports it.
- Its unit, identity, provenance and time semantics.
- Its loading, unavailable, stale and failure behavior.
- Any existing interaction that must be preserved.

Use a compact field-to-UI mapping for changed data-bearing components. Treat reference screenshots as visual requirements and illustrative content. The contracts and actual API capabilities determine which values can be displayed. Escalate a genuine contract gap through the appropriate project owner. Keep the frontend task within its specified boundaries.

## 2. Plan and review before implementation

Create a short design plan before changing code:

1. Identify the page's main operational purpose and the most important information.
2. Inspect the matching image in frontend-design-sample/ when supplied by the task.
3. Choose a compact token system for color, typography, spacing, borders and status indicators.
4. Sketch the desktop layout and describe how each region reorganizes at narrow widths.
5. Identify reusable components, required states and likely regressions.
6. Review the plan against the brief, existing behavior and available data. Refine any unclear hierarchy or ineffective visual choice.

Keep the two-pass process from the original skill: design and critique the plan, then implement and visually critique the result. Avoid extensive design exploration when an approved reference already defines the visual direction.

## 3. Use a consistent visual system

Follow the approved reference and reuse existing project tokens wherever possible. For the current SDV soft operations board, the following palette provides starting points. Verify text contrast and adjust shades where needed.

| Role | Suggested color |
|---|---|
| Page background | #F6F7FA |
| Panel surface | #FFFFFF |
| Text | #202633 |
| Secondary text | #586273 |
| Border | #D8DEE7 |
| Sage accent | #71977F |
| Powder blue surface | #E3EDF5 |
| Sage surface | #E7F0E6 |
| Muted orange surface | #FBECDD |
| Dusty rose surface | #F6E2E5 |
| Lavender surface | #EEEAF6 |

Use the colored surfaces sparingly to group information. Use darker foreground colors for readable text, especially on tinted cards and status badges.

- Reserve green for confirmed healthy, available or successful states in context. Use amber for warnings or stale data, red for critical faults or failed operations, and neutral tones for unknown data. Use text and icons to distinguish states that share a color. Never infer health from availability.
- Use a readable local sans-serif stack, a deliberate type scale and tabular numerals for changing values where supported. Keep labels in sentence case. Preserve meaningful technical identifiers verbatim.
- Establish a small spacing scale, aligned edges, consistent panel padding and modest corner radii. Use hierarchy and whitespace to group related data. Use borders only where they help distinguish regions or rows.
- Reuse the same navigation, controls, badges and terminology across Fleet, Vehicles, Diagnostics and Performance. Highlight the active page and selected vehicle clearly.
- Match the approved visual direction without decorative gradients, unnecessary labels, repeated shadows or animation that distracts from telemetry.
- Respect reduced-motion preferences. Keep polling updates stable so changing data does not continually shift the layout or steal focus.

## 4. Design around the page's responsibilities

**Fleet:** Surface registered vehicles, fleet counts, health and availability, selected-vehicle summary and observation details. Give operators a clear path to detailed telemetry and diagnostics. Derive counts from the fleet response according to the contract.

**Vehicles:** Prioritize selected-vehicle identity, available telemetry with units, sensor validity, provenance, active faults and recovery. Use recorded history for trends only when supported by the data source.

**Diagnostics:** Identify the target vehicle prominently. Present supported commands, current action and correlated history. Show command execution and observed health recovery independently. Retain action IDs when execution is uncertain. Respect existing authorization and action safeguards.

**Performance:** Display measured detection, propagation, recovery, coverage, throughput, latency or resource metrics when available. Show the run, stage, units, sample counts, timeouts and relevant measurement limits. Clearly identify illustrative fixtures. Compare stages only with appropriate context about measurement conditions.

Implement only the page and shared changes required by the current task. Preserve established entry URLs, navigation and the V1 default while V2 remains explicitly enabled through existing configuration.

## 5. Render truthful data and independent states

Use the current API contract and state model as the authority.

- Keep vehicle ID, Thing ID, event ID, source timestamp, evaluation timestamp, session/generation and sequence/frame distinct when provided. Display source age using the documented freshness rules. Preserve available source precision and units.
- Render each supported signal and its actual unit. Use the API's documented conversions or existing formatters. Typical SDV signals include speed, battery, coolant temperature, coolant pressure, tire pressure and LiDAR distance. Verify each field's availability and unit before displaying it.
- Use explicit provenance only when supplied by the data or supported configuration. Never infer CARLA origin from a vehicle ID or the presence of a distance value.
- Distinguish valid zero, null, absent, invalid and last-known values. A missing distance, for example, must not become zero meters or a clear scan.
- Render health, availability, active faults, recovery and source silence independently. A retained fault can remain active even when an accepted distance indicates a clear path. A clear command's success does not establish recovery.
- Render unavailable health as unknown when the API supplies no trusted health. Label retained stale data as last known. Never replace missing data with healthy values or misleading counts.
- Keep synthetic, fixture-based and live modes visibly distinct. Use fixture data only through the existing preview or test interface.
- Tie selected state and action history to the selected vehicle. Protect against late requests, overlapping polls and previous-vehicle replies. Use existing isolation mechanisms.
- Keep service credentials outside browser configuration, rendered content and screenshots. Use the project's established authorized gateway for protected operations.

Account for loading, normal availability, stale, unavailable, warning or critical faults, recovery in progress, source silence, empty history, request failure and uncertain action outcomes where applicable. Support only states and transitions defined by the current contract.

## 6. Implement responsive and maintainable components

Use the existing HTML/CSS/JavaScript architecture and rendering helpers. Keep transport, state management and presentation responsibilities clear. Reuse established formatting, status mapping, freshness and API logic.

Scope page-specific styles and reuse shared tokens. Avoid competing selector specificity, duplicated status rules and unnecessary dependencies. Use semantic headings, tables, buttons and labels. Preserve DOM hooks and accessible names required by existing behavior and tests.

Plan the narrow layout before writing CSS:

- Allow navigation and summary controls to wrap or adapt.
- Use a responsive grid for telemetry cards. Give values sufficient room for units and lengthy missing-data labels.
- Keep a semantic desktop roster. At narrow widths, stack fields with their labels and preserve each vehicle's accessible identity and selection behavior.
- Reflow metadata into readable groups. Allow long identifiers to wrap without expanding the page.
- Keep controls reachable without overlapping content or hiding important information.

Check desktop, intermediate and narrow layouts. Keep keyboard focus visible, logical tab order, accessible control names and readable contrast. Use labels and symbols alongside status colors. Ensure data refreshes preserve focus and avoid disruptive layout changes.

## 7. Verify the design and behavior

Use the task's acceptance criteria, applicable verification skill and existing test infrastructure. Establish the checks before implementing. Make assertions about observable behavior rather than the chosen CSS selector or mechanism.

Review the following when relevant:

| Check | Verification |
|---|---|
| Visual match | Compare screenshots with the supplied reference at the requested viewport. Review hierarchy, alignment, color, density and typography. |
| Data correctness | Check identities, units, fleet counts, missing fields, provenance and time labels with known inputs. |
| State correctness | Check stale, unavailable, retained-fault and recovering states. Check action success independently of recovery. |
| Interactions | Exercise selection, delayed responses, keyboard access, navigation and supported commands. |
| Responsive layout | Inspect a desktop viewport, an intermediate width and a narrow viewport. Check clipped text, roster labels, overlap and unwanted page overflow. |
| Accessibility | Check semantic structure, focus visibility, readable contrast and meaningful control names. |
| Maintainability | Review shared component use, scoped styles and preservation of existing public behavior. |

Run focused existing unit and browser tests for the changed page. Add a behavioral regression test for a specific uncovered risk when needed. Use existing V2 development fixtures and browser tooling for independent frontend work. Run live integration only when the task calls for it and prerequisites are available.

Capture the first completed implementation's screenshots and results before making review-driven corrections when the task is a skill comparison. Use representative states and consistent viewports. Recheck affected behavior after corrections. Record actual failures, fixes and remaining gaps.

For the current project, start with the existing frontend test commands and browser harness documented in the relevant evidence guide. Distinguish automated assertion results, visual inspection and manual accessibility checks. Report unexecuted checks as pending and identify synthetic versus live evidence. Preserve exact revisions and reproducible commands if evidence is requested.

## 8. Work efficiently

Read the selected page, its relevant contracts, shared styles and tests. Prefer existing dependencies and local tooling. Read broader project documents only when a relevant decision is unresolved.

Make one coherent implementation pass, then a bounded visual and functional review. Avoid repeated broad searches, redesigning unrelated pages, full-stack startup for static UI work, and polling CI repeatedly. Fix specific issues and rerun the affected checks. Keep commits and evidence aligned with the task's requested workflow.

Keep the implementation readable and the design purposeful. Give every visible element a role in understanding the vehicle, monitoring the fleet, taking an authorized action or interpreting the evidence.

## Derivation and license

Adapted from Anthropic's frontend-design skill:
https://github.com/anthropics/skills/tree/main/skills/frontend-design

Original supplied SKILL.md SHA-256:
d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3

Preserve the original upstream skill and applicable LICENSE.txt. Record the upstream revision from the original download when available. This derivative adds SDV-specific planning, semantic tokens, contract and state mapping, responsive layout guidance, component preservation, bounded verification and evidence requirements.
