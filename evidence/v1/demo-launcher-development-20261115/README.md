# Interactive launcher verification — November 15, 2026

Baseline main6fee175127c79ac28c3970eb5984b3dc7fa3b70d includes merged PR47; PR48
remains unmerged and unused. New code is orchestration only. Repository TDD and
verification-before-completion skills were read/applied; no supporting missing
skill is claimed. Red tests precede implementation; real preflight found provider
identity classification, captured by a failing regression before correction. A
contract fixture regression caught string fault handling before operator rehearsal.

Focused controls:11 PASS (green.txt), shell bash -n PASS, descriptor renderer PASS.
No complete Python/Java suite or full acceptance campaign rerun. Controls cover
duplicate Docker/unknown publishers, simultaneous Docker+Kanto, no restoration after
unverified cleanup, readiness deadline, three source boundaries, contract fault and
exact event matching, stale source despite runtime presence. Test cleanup failure
output is intentional and verified.

Read-only live rehearsals are retained in demo-20261115T233535Z and
demo-20261115T233814Z. Both exit1, not successful full demos. First exposed provider
classification; corrected run verifies actual001 fresh/two provider endpoints,002
stale/stopped, backend/dashboard absent; fleet Thing GET200. No service/scenario
mutation. Normal sudo authentication is unavailable in the agent session. The operator then completed the full working-copy sequence in
demo-20261115T234255Z: PASS, four narrated steps,101 validated MQTT messages
(including51 healthy001), clean managed stop/cleanup exit0. Owned backend/frontend
processes terminated, original Docker002 stayed stopped. See independent-review.json
in that directory. This run predates final metadata/fleet-lag retry/status/observer
close hardening; those final changes have focused coverage, not another full live run.
Restart fleet identities lagged while healthy; the final helper now retries exact
fleet identity rather than marking that step complete early. Docker-to-Kanto
transition from an initially running Docker app and supervised keep-running were
not exercised live; duplicate/refusal and failed-cleanup safety controls are unit-tested. The
launcher can start its prepared backend/dashboard when run interactively.

Persistent config: ~/.local/share/qa-sdv-v1/runtime/demo.json (secret-free example).
Prepared image/namespace, packaged backend Java21, active original prerequisites and
private credential prompts are documented in LINUX-RUNTIME.md. No installations,
image builds, twin/policy writes, volumes deleted, merges, tags or video recording.
