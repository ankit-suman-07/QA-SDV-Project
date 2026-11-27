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

## Run A design plan

Canvas #f6f6f8, ink #202538, sage #e3efe2, orange #fbeadb, rose #f8e7eb, lavender #eee8f7. A cool blue identifies LiDAR. Use a compact sans-serif scale with tabular counts and aligned values.

```
Brand | Fleet   Vehicle   Diagnostics   Performance
Fleet overview                              Refresh
[ Vehicles | Available | Stale | ... | Critical ]
[ Three registered vehicles, status side by side  ]
[ Selected vehicle ] [ LiDAR telemetry            ]
[                  ] [ Action execution |Recovery]
[ Latest observation details                      ]
```

The reference puts the operational roster first. The review of the initial plan replaced a generic multi-metric telemetry grid with a single LiDAR panel because the V2 projection supports it. Observation identity belongs in its own full-width strip, and the action panel stays adjacent to observed recovery so both can be inspected independently.
