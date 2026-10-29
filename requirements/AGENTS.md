# Requirements documents

`requirements/` contains the committed feature contracts for YARF. Read this
file before creating or reviewing a contract. Keep generated Spec Kit work
files under the ignored `specs/` directory. Do not commit generated plans,
tasks, checklists, or other ancillary files.

## Required format

Each feature has exactly one committed document at
`requirements/NNN-slug/requirements.md`, where `NNN` is a unique numeric ID of
at least three digits and `slug` is lowercase kebab case. The only other
permitted tracked file beneath `requirements/` is this `AGENTS.md` file.

The document uses these sections in this order:

1. `# Requirements: <feature name>`
1. `## Context`
1. `## User Stories`
1. `## Functional Requirements`
1. `## Success Criteria`

Write independently valuable, prioritized user stories as `### US-NN: <title> (Priority: PN)` headings, where `NN` has at least two digits and `PN` is `P1`
through `P5`. State the user, need, and outcome as
`As <user>, I want <capability>, so that <outcome>.` Give each story at least
one verifiable scenario in the form `- **Given** ..., **When** ..., **Then** ...`.
Use unique `FR-NNN` identifiers with exactly three digits. Each functional
requirement must be a Markdown bullet with a bold identifier, colon, and space,
followed by one of these EARS forms:

- `- **FR-NNN**: The system MUST ...`
- `- **FR-NNN**: When <event>, the system MUST ...`
- `- **FR-NNN**: While <state>, the system MUST ...`
- `- **FR-NNN**: Where <optional feature>, the system MUST ...`
- `- **FR-NNN**: If <condition>, then the system MUST ...`

Use `MUST NOT` instead of `MUST` for a prohibited behavior. For example:

```markdown
- **FR-001**: The system MUST retain each accepted requirement.
- **FR-002**: When approved, the system MUST record the decision.
```

Write unique `SC-NNN` success criteria with exactly three digits. Each must be a
Markdown bullet in the form `- **SC-NNN**: <observable outcome>` and include a
concrete numeric target with a unit or percentage. For example:

```markdown
- **SC-001**: The system reports a display state within 2 seconds.
- **SC-002**: At least 90% of status requests return the current state.
```

Keep requirements testable and focused on behavior, not implementation design.
Resolve placeholders and open questions before committing the contract.

## Lifecycle

Use Spec Kit to develop local working specifications. Adoption copies a
Spec Kit `spec.md` into the requirements tree as a starting point only. A
person must rewrite and review it in this format before it is committed.
Keep the committed contract current when scope, accepted behavior, or success
criteria change. Update the contract in the same pull request as the behavior,
or in a clearly ordered dependent pull request when the work is stacked. Do not
reuse a feature number for a different contract.

Run `make check-requirements` to check the tracked Git files. Newly created
contracts must be staged locally before this checker sees them. The checker
rejects tracked generated `specs/` files and tracked ancillary requirement
files.
