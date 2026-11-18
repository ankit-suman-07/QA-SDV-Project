# V2-07 systematic-debugging evaluation

Bayan compared the [checked-in original](../../../skills/systematic-debugging.md) and [customized v1.0.0](../../../skills/v2/systematic-debugging/SKILL.md) on one seeded vehicle-identity debugging scenario. The derivative adds a conditional Phase 1 procedure to state the invariant, trace observed identity and correlation across interfaces, identify the first violation, test a hypothesis, and verify the correction and unaffected entities. [Skill diff](../../../skills/v2/systematic-debugging/systematic-debugging-v1.diff) ? [Provenance and license](../../../skills/v2/systematic-debugging/PROVENANCE.md) ? [Course references](course-references.md)

The evaluated baseline was `4abc30f93c77fb05f6cecce16659fc603a33e6b5`. The eligible runs used identical seeded inputs, task prompt and benchmark-only package inventory. Each read and hashed its assigned skill before investigation. Launch records requested gpt-6.2-sol, medium reasoning, workspace-write with explicit MXC, approval never and sandbox tool networking disabled. The earlier process-policy-blocked attempt was excluded and preserved. Independent grading ran both corrected outputs in disposable copies with identical commands in a single offline locked environment.

| Measure | Original | Customized |
| --- | ---: | ---: |
| Correctness / regression quality / first divergence | 3/3, 2/2, 2/2 | 3/3, 2/2, 2/2 |
| Reproducibility and limitations / human corrections | 1/2, 1/1 | 1/2, 1/1 |
| **Total** | **9/10** | **9/10** |
| Private checks | 2 passed | 2 passed |
| Targeted suite | 85 passed, 119 subtests passed | 85 passed, 119 subtests passed |
| Agent elapsed time | 118.77 s | 296.22 s |
| Completed shell calls, including failures | 25 | 22 |

Both submissions showed a regression failing before the fix and passing afterward. Both lost the same reproducibility point because the agent reports omitted the tested source revision. No substantive human correction was observed. The customized run traced event identity and source time more explicitly, tested a single-variable hypothesis, and asserted exact request paths. It showed no measurable correctness advantage.

The original agent's broad pytest run stopped at missing dependency imports. The customized agent encountered an MXC-context loopback denial and deselected the affected test in its fallback. The full prescribed targeted suite passed for both outputs during independent host-side grading, including loopback. One sequential pair and one seeded scenario limit generalization. Existing tests exposed the symptom, scoring was partly blinded, and strict read isolation was unverified. These are fixture-backed results. This completes Bayan's V2-07 evaluation evidence, with team-wide acceptance outside this record.
