# Preface

Defines how contributors use Spec Kit to develop, adopt, and deliver feature
contracts in YARF.

Read the top-level `.kb/agents.md` file before continuing below.

# Important

## When to use Spec Kit

Use Spec Kit for a new feature that needs explicit user outcomes, functional
requirements, measurable success criteria, or coordination across components.
It is optional for a small, localized bug fix or maintenance change that has a
clear existing contract. Read the relevant contributor guidance and current
requirements before defining work.

## Agent integration

The repository uses Spec Kit's OpenCode integration as the default and also
installs the Pi Coding Agent integration. Spec Kit manages the equivalent
OpenCode and Pi command definitions in `.opencode/commands/` and `.pi/prompts/`.
They are invoked as `/speckit.<command>`, such as `/speckit.specify` and
`/speckit.plan`.

Other agent harnesses must follow this workflow and this document when working
on a Spec Kit feature. They must not copy, move, or hand-edit generated commands
into a harness-specific command or skill directory. Use the Spec Kit CLI to
change or upgrade an integration.

## Working files and committed contracts

Spec Kit calls its local draft a specification and writes it, plans, task
lists, and checklists under `specs/`. The root ignore rule keeps those working
files out of Git. The reviewed project contract is instead
`requirements/NNN-slug/requirements.md`. Do not commit generated plans, tasks,
checklists, or other ancillary files under `requirements/`.

The project workflow runs specify, clarify, plan, and task generation with
review gates. It ends after tasks have been reviewed. It does not authorize
automatic implementation of the whole feature in one branch. Resolve open
questions during clarification and review the proposed behavior, plan, and
tasks before implementation starts.

To adopt a generated spec, run:

```sh
make adopt-spec FEATURE=specs/NNN-feature-name
```

The helper copies `spec.md` into a unique requirements directory and leaves
the generated working files in `specs/`. It does not convert the document.
Rewrite and review the copied file using `requirements/AGENTS.md`, then run
`make check-requirements`. The checker validates Git-tracked files, so stage a
new local contract before checking it. Keep the contract current as accepted
behavior changes.

## Feature delivery and architecture decisions

Create a base pull request for a new Spec Kit feature after its contract is
adopted and reviewed. The base pull request targets `main` and contains the
feature's `requirements/NNN-slug/requirements.md`, the relevant contributor
and user documentation, and any required ADR. It contains no product
implementation.

Map each accepted user story, `FR-*` requirement, and success criterion to an
implementation deliverable. Name the component, behavior, and tests for each
deliverable and preserve dependency order. Add each deliverable above the base
pull request as a dependent layer. Tests travel with the behavior they verify.
Keep tightly coupled behavior and its tests together when splitting them would
make review or validation misleading. If a review changes the contract, amend
the base pull request and rebase its implementation layers.

Requirements state intended behavior and measurable outcomes. Use an ADR under
`adr/` for a non-obvious, durable architectural decision such as a new process
boundary, public contract, or dependency direction. Do not use an ADR to
duplicate feature requirements or record ordinary implementation choices.

An unmerged branch that tracks `specs/` files must migrate them to the
requirements format on its own stack before it can merge. Keep that migration
separate from this foundation and do not merge generated `specs/` artifacts.
