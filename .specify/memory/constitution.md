# YARF Constitution

## Core Principles

### I. Robot Framework Contract Ownership

YARF must remain predictable and diagnosable for automation authors. Changes
to Robot Framework keywords, command-line options, configuration values,
platform plugins, output formats, or Snap behavior must preserve documented
contracts, report actionable failures, and identify affected consumers.

The implementation under `yarf/` is the authoritative source for YARF's CLI,
Robot Framework libraries, platform plugins, and internal helpers. Generated
library documentation and test suites must remain consistent with a changed
public keyword or plugin.

### II. Small, Direct Changes

Keep a change within one component unless implementation, generated
documentation, tests, packaging, or a public contract requires a broader
scope. This constitution sets repository-wide requirements. Closer `AGENTS.md`
files may refine or strengthen them, but must not relax a mandatory repository
constraint, including the requirements and Spec Kit policy.

Prefer simple, direct implementations. New abstractions, dependencies,
compatibility layers, and extension points require a demonstrated current need.
Do not make unrelated refactors while delivering a feature or fix.

### III. Evidence-Based Quality

Changed behavior must be covered by focused automated tests, or the change
must document why automation is not practical and how the behavior was
otherwise verified. Run the relevant documented formatting, lint, build, and
test commands before considering work complete.

Keyword, CLI, configuration, plugin, output, Snap, and documentation changes
require verification at the relevant boundary. Tests and checks must be
proportionate to the risk and must not rely on an unavailable platform unless
the package explicitly requires it.

### IV. Explicit Compatibility and Release Integration

Public interfaces, including CLI options, configuration values, Robot Framework
keywords, platform plugins, output formats, Snap behavior, and documentation,
are product contracts. Identify affected consumers before changing such an
interface, preserve backward compatibility where practical, and explicitly
call out intentional breaking behavior.

Packaging changes must keep `snap/`, `GitVersion.yaml`, and the documented
Snap build assumptions consistent. Generated Robot library documentation must
be updated when a changed library requires it.

### V. Secure Stewardship and Traceable Decisions

Treat source, documentation, and operational details according to the
repository's confidentiality requirements. Preserve repository controls,
including Git LFS where it manages assets and signed commits.

Keep user-facing and contributor documentation consistent with implemented
behavior. Record non-obvious, long-lived structural choices, such as a new
process boundary, public contract, or dependency direction, in an ADR under
`adr/` with its alternatives and consequences.

## Engineering Constraints

- YARF uses `uv`, `tox`, and `prek` for dependency management and quality
  checks. Tox targets Python 3.10, 3.12, 3.13, and 3.14.
- Public Python modules generally require module docstrings. Docstrings use
  Google style and the configured line length is 79 characters.
- Tests must be safe for parallel execution because tox runs pytest with
  `-n=auto`.
- Generated files under `yarf/lib/wayland/protocols/` are changed only for work
  that specifically requires generated Wayland protocol code.
- Versioning is determined in CI by GitVersion.

## Delivery and Review Workflow

1. Establish the affected components, public contracts, packaging impact, and
   consumer impact before implementation.
2. Read the applicable `AGENTS.md` and use its commands and conventions.
3. Implement the smallest complete change and add or update focused tests and
   documentation with it.
4. Run applicable validation. Report commands not run, unavailable platforms,
   and residual integration risk clearly.
5. During review, verify scope, contributor guidance, tests, keyword or plugin
   coverage, packaging consistency, and documentation accuracy.
6. Use a signed commit and a pull request title carrying exactly one of
   `[Infra]`, `[BugFix]`, `[New]`, or `[Breaking]`.

## Governance

This constitution defines minimum repository-wide engineering requirements and
supersedes conflicting informal practices. Closer `AGENTS.md` files may refine
or strengthen these requirements, but must not relax mandatory repository
constraints, including the requirements and Spec Kit policy. If local guidance
conflicts with a mandatory repository constraint, this constitution governs.

Amendments require an explicit change to this document, a rationale, and a
version increment following semantic versioning: MAJOR for removed or
materially redefined principles, MINOR for new principles or material guidance,
and PATCH for clarifications. Plans, specifications, implementation work, and
reviews must verify compliance with the current constitution. Deviations need a
documented, time-bounded justification and owner.

**Version**: 1.0.0 | **Ratified**: 2026-10-29 | **Last Amended**: 2026-10-29
