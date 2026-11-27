# Architecture Decision Records

This directory records notable architecture decisions for this repository.

## Index

| #                                              | Title                                         | Status   | Date       |
| ---------------------------------------------- | --------------------------------------------- | -------- | ---------- |
| [0001](0001-yarf-github-action.md)             | YARF GitHub Action for running tests in CI    | Accepted | 2026-08-12 |
| [0002](0002-llm-test-tracing-opentelemetry.md) | Record LLM test traces as OpenTelemetry files | Proposed | 2026-11-15 |

## Conventions

- One file per decision, named `NNNN-<adr-name>.md` (e.g. `0001-yarf-github-action.md`),
  where `NNNN` is a zero-padded, incrementing number.
- Use the sections Context, Decision, and Consequences. Add
  `Alternatives considered` when a reader would otherwise ask why an obvious
  option was rejected.
- Statuses: `Proposed`, `Accepted`, `Superseded by NNNN`, `Deprecated`.
- Never delete a superseded ADR or rewrite its decision. Change only its status
  to `Superseded by NNNN`, and let the new ADR explain what changed.
- Add a row to the index above when creating a new ADR.
- Dates use ISO 8601 (`YYYY-MM-DD`) and record when the decision was made.

## Writing an ADR

An ADR explains one technical decision to a person who knows YARF but was not
part of the discussion.

- Record one decision. An ADR does not describe a feature, an epic, or a
  delivery plan. A feature with two durable decisions gets two ADRs, and most
  features need none.
- Write for a human reader. Use short prose that a reviewer can read in a few
  minutes. Use a table, code block, or example only when the decision itself
  is about that shape, such as a file format or an identifier scheme.
- State what was decided and why, not how it is built. Leave out module,
  function, script, and file names, input lists, call sequences, configuration
  values, and timings unless the decision cannot be stated without them.
- Do not restate the requirements. Behavior, scope, keyword lists, and
  acceptance criteria belong in `requirements/NNN-slug/requirements.md`. Link
  to it instead.
- Limit Context to the facts the decision rests on, such as a Snap confinement
  rule, a platform constraint, or upstream behavior, so a later reader can
  re-test the premise. Do not survey the code base.
- Give each alternative one or two sentences that name why it was rejected.
- List in Consequences the lasting effects a later contributor must respect.
  Do not list follow-up tasks.
- Keep it concise. Aim for about 400 words. An ADR that approaches the length
  of its requirements document is doing the requirements' job.

## References

- [Michael Nygard's ADR template](https://github.com/joelparkerhenderson/architecture-decision-record)
- [ADR GitHub Organization](https://adr.github.io/)
