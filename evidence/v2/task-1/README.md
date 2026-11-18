# Bayan Phase V2 Task 1 evidence

This record covers isolated native diagnostic feasibility and Bayan's completed customized-skill evaluation. The two protocol probes exercised real transports with fixture data. Live selected-vehicle wiring, team approval of production bindings, and full V2-06 production integration and acceptance remain pending.

| Evidence | Status |
| --- | --- |
| [uProtocol health RPC](uprotocol-feasibility.md) | Native fixture request/response, correlation and bounded timeout verified over MQTT 5. |
| [OpenSOVD fault reads](opensovd-feasibility.md) | Linux ARM64 builds and native DoIP/UDS fault scenarios verified with the official simulated ECU. |
| [V2-07 skill evaluation](skill-evaluation.md) | Bayan's paired evaluation and independent grading completed. Both variants scored 9/10. |
| [Reproduction](reproduction.md) and [course references](course-references.md) | Archived inputs and commands are available to authorized reviewers. Assigned textbook status is pending. |

## Scope and next decisions

The [earlier source-inspection note](../../../docs/v2-native-diagnostic-feasibility.md) records preparation-time candidates and constraints. The fixture runs here add execution evidence for the Rust stack and a later pinned CDA revision. The existing Java pin, project telemetry, adapters, and [V2-C6 development boundary](../../../docs/v2-interface-contracts.md) retain their current roles. The probe bindings are candidates for review.

- **Ankit:** Confirm the supported production providers, selected-vehicle mapping to method URI and CDA component, diagnostic response and error mapping, action/trace correlation, deadline, fault scopes, permissions, and backend integration boundary.
- **Emmanuel:** Confirm the authoritative live observations and fault inputs, source identity and replay handoff, deployment and authentication dependencies, and the health and availability handoff. Coordinate ownership with Ankit and Bayan under the [current owner-specific plan](../../../docs/13-FINAL-phase-v2-tasks-and-acceptance.md).
- **Live verification:** Execute the agreed operations with authoritative selected-vehicle inputs. Record source-linked healthy and fault results, identity/correlation, failure, unavailable and deadline behavior. [Project acceptance](../../../docs/08-project-scope-and-acceptance.md)
