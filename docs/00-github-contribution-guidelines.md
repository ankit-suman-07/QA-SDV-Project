# GitHub Contribution Guidelines

## Purpose

These guidelines define the minimum GitHub workflow for the Software-Defined Vehicle Health Monitoring and Diagnostic System. The goals are to keep `main` stable, reduce integration conflicts, support test-driven development, and make every contribution reviewable.

All team members must follow this guide.

## 1. Standard Workflow

Do not commit directly to `main`.

For every task:

1. Update your local `main` branch.
2. Create one focused branch.
3. Write or update the agreed tests before implementation where applicable.
4. Implement the smallest change needed to satisfy the task.
5. Run the relevant tests locally.
6. Push the branch and open a pull request.
7. Obtain at least one team-member approval.
8. Resolve important review comments.
9. Merge only when the definition of done is satisfied.

```bash
git switch main
git pull origin main
git switch -c <member>/<type>/<short-description>
```

## 2. Branch Naming

Use:

```text
<member>/<type>/<short-description>
```

Rules:

- Use lowercase letters and hyphens.
- Keep the description short and specific.
- Keep one task or closely related change per branch.

| Type | Use |
|---|---|
| `feature` | New functionality |
| `fix` | Bug correction |
| `test` | Test-only changes |
| `docs` | Documentation |
| `refactor` | Internal improvement without behavioural change |
| `config` | Build, Docker, CI, or environment configuration |
| `research` | Time-boxed feasibility investigation |

Examples:

```text
ankit/feature/health-engine
emmanuel/feature/kuksa-simulator
benjamin/feature/fault-events
atharva/feature/ditto-sync
mehtaj/feature/health-dashboard
ankit/test/health-boundaries
benjamin/config/jenkins-pipeline
```

## 3. Commit Messages

Use:

```text
<type>: <short description>
```

Use lowercase types: `feat`, `fix`, `test`, `docs`, `refactor`, `config`, or `research`.

Examples:

```text
feat: detect critical temperature fault
test: add battery recovery boundary cases
fix: preserve source timestamp during ditto mapping
docs: record verified kuksa signal paths
config: add backend test stage to jenkins
```

Each commit should represent one logical change. Do not use messages such as `update`, `changes`, `fixed stuff`, or `done`.

## 4. Test-Driven Development

For agreed behaviour, follow this cycle:

1. Define the expected behaviour and acceptance criteria.
2. Add a test that fails for the expected reason.
3. Implement the minimum code required for the test to pass.
4. Run the relevant existing tests.
5. Refactor while keeping all tests green.

Component owners are responsible for their component-level tests. Ankit owns backend, API-contract, integration, end-to-end, latency, reliability, and overall quality analysis.

Tests are required for agreed behaviour. If automated testing is technically impractical for a task, the pull request must include repeatable manual verification steps and evidence.

## 5. Pull Requests

Every change to `main` requires a pull request.

### Pull Request Title

Use the same style as commit messages:

```text
feat: add low-battery fault injection
test: validate uprotocol fault serialization
docs: finalize vehicle health contract
```

### Required Description

Use this template:

```markdown
## Summary

Briefly explain what changed and why.

## Related Task

Day/task or issue: 

## Changes

- Change 1
- Change 2

## Testing

- Test command or manual procedure
- Result

## Evidence

Add relevant logs, API output, screenshots, or recordings.

## Dependencies and Handoffs

State who is affected and what they need to do next.

## Known Limitations

List limitations, or write `None known`.
```

Keep pull requests focused and small enough to review. Do not mix unrelated documentation, refactoring, and feature work unless they are necessary for the same task.

## 6. Review and Merge Rules

Before merging:

- At least one team member must approve the pull request.
- A change to a shared contract must be reviewed by every affected component owner.
- The author must resolve important comments.
- Required checks and relevant tests must pass.
- Merge conflicts must be resolved.
- Temporary debugging code and secrets must be removed.

The author must not approve their own pull request. For high-impact integration changes, Ankit should participate in the review.

Use the repository's agreed merge strategy consistently. **Squash merge** is recommended for short-lived task branches so `main` remains readable.

Delete the branch after a successful merge.

## 7. Shared Contract Changes

The following must not be changed silently:

- Logical field names, types, or units
- Kuksa/VSS paths
- Health thresholds or recovery rules
- Fault codes or severity behaviour
- REST or real-time API structures
- uProtocol message fields or event behaviour
- Ditto properties
- OpenSOVD diagnostic mappings
- Dashboard-facing field names

A contract-changing pull request must:

1. Explain the reason for the change.
2. Identify affected components and owners.
3. Update the authoritative contract document.
4. Update affected tests and examples.
5. Receive approval from affected owners before merge.

## 8. Definition of Done

A task is complete only when:

- The agreed acceptance criteria are satisfied.
- The implementation works in the intended environment.
- New or changed behaviour has appropriate tests.
- Relevant existing tests pass.
- No known critical regression remains.
- Configuration is not hard-coded unnecessarily.
- Logs and error handling are adequate for diagnosis.
- Required documentation or contract fields are updated.
- Evidence is included in the pull request.
- Dependencies and handoffs are communicated.
- At least one reviewer approves the pull request.
- The change is merged into `main`.

Completing code locally or opening a pull request does not by itself complete the task.

## 9. Keeping Branches Current

Update long-running branches regularly, especially before integration:

```bash
git switch main
git pull origin main
git switch <your-branch>
git merge main
```

Resolve conflicts promptly with the affected owner. Do not overwrite another member's work to make a conflict disappear.

## 10. Code and Repository Quality

Before pushing:

- Format the changed files.
- Remove unused imports and temporary debug statements.
- Run the relevant application or component.
- Run relevant tests.
- Review your own diff.
- Confirm no secret or personal file is included.

Do not commit:

- Passwords, tokens, keys, or credentials
- `.env` files containing real values
- IDE-specific personal settings
- Build outputs such as `target/`, `build/`, or `dist/`
- Dependency folders such as `node_modules/`
- Logs, temporary files, or operating-system files

Provide safe configuration examples through files such as `.env.example` where needed, and keep `.gitignore` current.

## 11. Dependencies and Structural Changes

Before adding a dependency or making a major structural change:

1. Explain the need to affected team members.
2. Check compatibility with the selected Java, component, and container versions.
3. Record any setup impact.
4. Add or update the appropriate test.
5. Obtain approval from the affected owner.

Major changes include architecture changes, API changes, shared model changes, directory reorganizations, and replacement of an agreed integration approach.

## 12. Daily Communication

Each member should record concise daily progress in the team's project-management system or daily progress document:

- Completed work and pull-request link
- Test or demonstration evidence
- Current blocker
- Dependency or handoff needed
- Next task

Raise blockers as soon as they are discovered. Do not wait until the end of the day or integration period if another member is affected.

## Quick Checklist

Before requesting review:

- [ ] Branch follows the naming convention.
- [ ] Change is focused on one task.
- [ ] Acceptance criteria are satisfied.
- [ ] Relevant tests pass.
- [ ] Shared contracts are updated if affected.
- [ ] No secrets, build outputs, or debug code are included.
- [ ] Pull-request description includes testing and evidence.
- [ ] Dependencies and handoffs are identified.

