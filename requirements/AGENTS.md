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
2. `## Context`
3. `## User Stories`
4. `## Functional Requirements`
5. `## Success Criteria`

Write independently valuable, prioritized user stories as `### US-NN: <title>
(Priority: PN)` headings. State the user, need, and outcome as
`As <user>, I want <capability>, so that <outcome>.` Give each story at least
one verifiable scenario in the form `- **Given** ..., **When** ..., **Then** ...`.
Use stable, unique `FR-NNN` identifiers for functional requirements.
Each functional requirement uses an unambiguous EARS form, such as:

- `The system MUST ...`
- `When <event>, the system MUST ...`
- `While <state>, the system MUST ...`
- `Where <optional feature>, the system MUST ...`
- `If <condition>, then the system MUST ...`
- Use `MUST NOT` for a prohibited behavior.

Write `SC-NNN` success criteria as observable outcomes with a concrete numeric
target and unit or percentage. Keep requirements testable and focused on
behavior, not implementation design. Resolve placeholders and open questions
before committing the contract.

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
