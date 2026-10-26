# Preface

Covers how YARF pull requests are scoped, described, reviewed, and updated.
Read this before opening, updating, or reviewing a pull request.

Read the top-level `.kb/agents.md` file before continuing below.

# Overview

YARF is a Python package with Robot Framework libraries, platform plugins, and
user documentation. A pull request should make one understandable change,
include the tests that demonstrate it, and identify effects on generated
library documentation, the Snap, and supported platforms where relevant.

The root `AGENTS.md` provides the repository guide. `CONTRIBUTING.md` defines
the development workflow. The pull request template defines the GitHub
sections that CI requires.

# Important

- Keep a pull request focused on one behavior. Do not combine unrelated
  cleanup with a feature or fix.
- Include changed behavior tests in the same pull request. Explain when a test
  is not practical.
- Run the applicable formatters, linters, tests, and documentation checks.
  Record commands that were not run and the reason.
- Update generated library documentation when a change under
  `yarf/rf_libraries/` requires it.
- Use signed commits.

## Scope and compatibility

A pull request normally changes one component. Change multiple components when
the implementation, generated documentation, tests, packaging, or a public
contract requires it. Describe that dependency in the pull request.

Check users of a changed CLI option, configuration value, Robot Framework
keyword, platform plugin, output format, or Snap behavior. A breaking change
identifies affected users and provides a migration or replacement path.

Do not split a behavior change from the tests that show it. When a change
introduces a new keyword, decide whether it needs Robot keyword coverage under
`tests/keyword_suite/`, plugin coverage under `tests/plugin_suite/`, or smoke
coverage under `tests/canary_test/`.

## Title and description

The title begins with exactly one traceability tag:

- `[Infra]` for documentation, comments, or GitHub Actions only.
- `[BugFix]` for a bug fix.
- `[New]` for a backward-compatible feature, test, or test plan.
- `[Breaking]` for a backward-incompatible change.

CI validates the title and the sections in `.github/pull_request_template.md`.
Start the description with a short overview of the problem, change, and scope.
Follow it with the changed behavior, interface or compatibility effect,
important implementation decisions, persisted or output-data changes, and
documentation effect. Include an example when a data format changes.

Do not provide a line-by-line account of the diff. The documentation and test
sections identify documentation changes, commands run, environments used, and
manual validation steps. State when the change has no user-visible
documentation effect or when a relevant check was not run.

## Review feedback

Read every review and inline comment before requesting another review. Resolve
a finding by fixing it and naming the commit in the thread, or by explaining
why the current approach is correct or why the request is outside the pull
request scope. Do not resolve a thread without an outcome.

## Before requesting review

- Read `AGENTS.md` and the guidance for every changed area.
- Run the checks documented by `CONTRIBUTING.md` and `docs/CONTRIBUTING.md`.
- Run `make -C docs libdoc-convert` when changing Robot library source.
- Confirm user-facing CLI, keyword, configuration, plugin, Snap, and
  documentation changes remain consistent.
- Include reproducible manual validation steps when automated checks cannot
  cover a platform or hardware-dependent change.
- Check that the signed commits and required CI workflows are present.
