# Phase V1 verification run — 20261115T023010Z

Initial real-stack attempt: readiness FAIL due the harness using 127.0.0.1:3000 outside the existing backend CORS allowlist. Both scenarios cleared and owned projects stopped. No downstream acceptance. Tool exit 2. This attempt predates exact harness-source capture; manifest SHA/dirty state and command outputs are retained without claiming clean-source reproducibility.

[Manifest](manifest.json) · [Results](results.json) · [Commands/exits](commands.json) · [Artifact hashes](artifact-sha256.json)

[Detailed dated findings](../../../docs/findings/v1-implementation-verification.md#follow-up--2026-11-15-utc-integrated-acceptance-on-an-isolated-prepared-deployment). Credentials are excluded. Root-level evidence remains in place.

Text command/service outputs were authentication-redacted and trailing whitespace
normalized before durable tracking; source/event IDs, timestamps, results and exits
are preserved. Hashes cover the reviewed secret-free artifacts.
