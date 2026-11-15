# Phase V1 verification run — 20261115T023435Z

Unmodified real Ditto deployment: healthy FAIL; missing v1 feature caused ingress PUT404 and the packaged Spring client's duplicate Accept-Encoding caused HTTP400. Direct HTTP probes and the packaged-client Java reproduction are included. Two operation timeouts retained; run interrupted with SIGTERM through cleanup, tool exit130; later gates not reached. No complete acceptance. Captured harness source identifies the dirty implementation.

[Manifest](manifest.json) · [Results](results.json) · [Commands/exits](commands.json) · [Artifact hashes](artifact-sha256.json)

[Detailed dated findings](../../../docs/findings/v1-implementation-verification.md#follow-up--2026-11-15-utc-integrated-acceptance-on-an-isolated-prepared-deployment). Credentials are excluded. Root-level evidence remains in place.

Text command/service outputs were authentication-redacted and trailing whitespace
normalized before durable tracking; source/event IDs, timestamps, results and exits
are preserved. Hashes cover the reviewed secret-free artifacts.
