# Copilot instructions - YARF

## Overview

YARF, Yet Another Robot Framework, is a Python package built on Robot
Framework for visual and platform test automation. The CLI entry point is
`yarf.main:main` and the main keyword/platform code lives under
`yarf/rf_libraries/`, with support code in `yarf/lib/` and custom exceptions
in `yarf/errors/`.

______________________________________________________________________

## Code review checklist

When reviewing a pull request, verify the following:
Prefer simple, direct solutions in reviews. Flag unnecessary abstraction,
speculative extension points, or new dependencies when they are not justified
by the current change.

### PR hygiene

- [ ] The PR title starts with exactly one of `[Infra]`, `[BugFix]`, `[New]`,
  or `[Breaking]`. CI enforces this but flag it if missing, misplaced, or
  duplicated.
- [ ] All commits are signed. The PR template states that signed commits are
  required.
- [ ] The PR description fills in the template sections: Description,
  Resolved issues, Documentation, Tests.
- [ ] Changes that affect persistence or output formats include examples or
  enough detail in the PR description for reviewers to validate compatibility.

### Code quality

- [ ] Python changes pass `ruff`, `ruff-format`, `isort`, `mypy`,
  `docformatter`, `interrogate`, `pydoclint`, and `licensecheck` through
  `uv run prek run --all-files --hook-stage manual` or `uv run tox`.
- [ ] Python line length is 79 characters, matching `pyproject.toml`.
- [ ] Public Python modules include module docstrings unless covered by an
  existing per-file ignore. Docstrings use Google style.
- [ ] New code is compatible with the supported Python range in
  `pyproject.toml`: Python 3.10.12 through 3.14, excluding 3.11.0 - 3.11.3.
- [ ] Robot Framework files pass the configured Robocop formatting and lint
  rules.
- [ ] Avoid modifying `yarf/vendor/` or generated Wayland protocol files under
  `yarf/lib/wayland/protocols/` unless the change is specifically about
  vendored or generated code.

### Tests

- [ ] New or changed Python behaviour is covered by pytest tests. `tox` runs
  `pytest -n=auto --cov=yarf --cov-fail-under=100`, so coverage must remain at
  100% for `yarf`.
- [ ] Tests are safe to run in parallel because tox enables `pytest-xdist`.
- [ ] Keyword changes include Robot coverage under `tests/keyword_suite/` when
  applicable.
- [ ] Any keyword intentionally excluded from keyword coverage uses the
  `yarf: nocoverage` tag or comment and explains why, or links to the relevant
  issue.
- [ ] Platform plugin changes are covered by `tests/plugin_suite/` when
  applicable.
- [ ] Smoke or end-to-end behaviour changes are reflected in
  `tests/canary_test/` when applicable.

### Generated keyword documentation

- [ ] If files under `yarf/rf_libraries/**/*.py` change, generated library
  documentation under `docs/` is updated. The pre-commit hook checks this with
  `make -C docs libdoc-convert`.

### Documentation

- [ ] Documentation changes under `docs/` follow the MyST/Sphinx starter-pack
  conventions described in `docs/CONTRIBUTING.md`.
- [ ] Docs-only checks are run when relevant, especially spelling, linkcheck,
  inclusive language, style, Markdown linting, and accessibility checks.
- [ ] Significant new features, breaking changes, or new keywords include
  documentation updates or an explicit follow-up.

### Snap and release changes

- [ ] Snap changes under `snap/` are validated with the snap workflows or a
  local `snapcraft pack` when practical.
- [ ] Versioning or release changes account for the GitVersion-based SemVer
  flow used by `scripts/semver.sh` and the release workflows.

______________________________________________________________________

## Component-specific notes

### `yarf/main.py`

- Contains CLI startup and option handling for the `yarf` command.
- Validate user-facing CLI changes with tests and documentation updates.

### `yarf/rf_libraries/`

- Contains Robot Framework libraries, resources, interactive-console support,
  parser code, and variables.
- Keyword additions or signature changes must keep generated docs and keyword
  coverage in sync.

### `yarf/rf_libraries/libraries/mir/`

- Mir/Wayland platform implementation. Tests may require system Wayland/Mir
  dependencies and a system-Python-backed uv environment because uv-managed
  Python builds lack `os.memfd_create`.

### `yarf/rf_libraries/libraries/vnc/`

- VNC platform implementation. Preserve parity with Mir where shared keyword
  behaviour is expected.

### `yarf/lib/`

- Internal helpers, including Wayland support. Generated protocol files under
  `yarf/lib/wayland/protocols/` are excluded from normal style and coverage
  expectations.

### `tests/`

- `tests/keyword_suite/` contains Robot keyword coverage tests.
- `tests/plugin_suite/` contains platform plugin tests.
- `tests/canary_test/` contains smoke tests used by CI.

### `docs/`

- Documentation is built with Sphinx and MyST using Canonical's starter-pack
  conventions.
- Reference pages for Robot libraries are generated; do not hand-edit generated
  output when the source keyword docstrings should change instead.
