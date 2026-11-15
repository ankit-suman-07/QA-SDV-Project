# Combined recovery + pressure verification — 2026-11-15 UTC

Production merge `470240d` combines existing PR #39 head `d6b770c` and main
`ed5016c` (merged PR #38). Four new unit regressions and fresh evidence were dirty
at execution; source hashes identify these exact inputs. Prior evidence is preserved.

[Full dated follow-up](../README.md#combined-follow-up--2026-11-15-utc-after-pr-38-merged)
· [Check summary](checks.json) · [Static/source review](combined-review.json)
· [Runtime manifest](runtime-manifest.json) · [Actual results](runtime-results.json)
· [Commands/exits](runtime-commands.json) · [Versions](runtime-versions.json)
· [MQTT capture](runtime-mqtt.jsonl) · [Baseline](baseline-results.json)
· [Artifact hashes](artifact-sha256.json).

All combined checks passed. Actual boundaries: both providers/KUKSA/apps/MQTT,
broker outages, startup/shutdown, known controlled generator pressure and readback.
Conversion/protobuf/mapper execute in-process with explicit diagnostic context;
full legacy bridge HTTP/real Ditto/OpenSOVD and Kanto are not verified by this run.
No credentials used or recorded. Cleanup stopped only owned projects without volume
deletion. Text outputs normalize trailing whitespace without changing outcomes.

The existing provider-recovery and tire-pressure unit records remain historical.
