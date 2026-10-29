# Preface

Fast guide for coding agents working in YARF. Keep this file concise. Use
`CONTRIBUTING.md`, `docs/CONTRIBUTING.md`, and `.kb/` for detailed contributor
guidance.

Read the top-level `.kb/agents.md` file before continuing below.

# Overview

## What this repo is

- `yarf` is a Python package built on Robot Framework for visual/platform test
  automation.
- CLI entrypoint: `yarf.main:main` -> `yarf`
- Main platform/keyword code lives in `yarf/rf_libraries/libraries/`
  (`mir/`, `vnc/`, `ocr/`, `image/`, `geometry/`, `llm_client/`, shared bases).

## Where to look first

- `yarf/main.py` - CLI startup
- `yarf/rf_libraries/` - Robot Framework libraries, parser, resources, variables
- `yarf/lib/` - internal helpers, including Wayland support
- `yarf/errors/` - custom exceptions
- `tests/keyword_suite/` - Robot keyword coverage tests
- `tests/plugin_suite/` - platform plugin tests
- `tests/canary_test/` - smoke tests
- `**/tests/` under `yarf/` - Python unit tests are mostly colocated

# Important

## Normal workflow

```bash
uv sync
uv run pytest
uv run pytest path/to/test_file.py -k test_name
uv run tox
uv run prek run --all-files --hook-stage manual
```

Notes:

- `.python-version` is `3.12`, but tox targets 3.10, 3.12, 3.13, 3.14.
- `tox` is the best "full repo" check: it runs manual `prek` hooks plus pytest
  with coverage. `prek` is the project's pre-commit tool (wraps
  `pre-commit`).
- Pytest runs with `--doctest-modules` and `-n=auto` (pytest-xdist) in tox, so
  tests must be safe for parallel execution.
- For local runs/tests, install the system packages from `CONTRIBUTING.md`,
  for example:
  `sudo apt install -y build-essential libxkbcommon-dev tesseract-ocr`.
  Optional: `python3-tk`. See `CONTRIBUTING.md` for the full setup guide.

## Repo-specific guardrails

- Line length is **79**.
- Public Python modules generally need module docstrings (`D100` is enforced).
- Docstrings use Google style; `docformatter` is configured with
  `--pre-summary-newline`.
- `mypy` runs with `--check-untyped-defs`.
- Coverage for `yarf` is gated at **100%** in tox.
- To exclude a keyword from keyword coverage, use `yarf: nocoverage` and explain
  why.
- Avoid editing `yarf/lib/wayland/protocols/` unless the task is specifically
  about generated code.
- `yarf/vendor/` is third-party code maintained in-tree: it follows the same
  lint, typing, docstring and coverage rules as the rest of `yarf`. Record
  modifications in the `NOTICE` file of the vendored package.

## Easy-to-miss checks

- If you change files in `yarf/rf_libraries/**/*.py`, pre-commit also checks that
  generated library docs under `docs/` are up to date via
  `make -C docs libdoc-convert`.
- Docs-only checks such as spelling/link/inclusive-language/style/accessibility
  exist in prek manual hooks; run them when touching `docs/`.

## Before making broad changes

- Read `CONTRIBUTING.md` if the change affects packaging, Snap builds, docs, or
  keyword coverage policy.
- Read `.kb/pull-requests.md` before opening, updating, or reviewing a pull
  request.
- Read `.kb/writing-style.md` before writing contributor documentation, pull
  request text, review comments, commit messages, or agent replies.
- Read `.kb/documentation.md` and `docs/AGENTS.md` before changing user-facing
  behavior or documentation.
- Read `.kb/spec-kit.md` before starting or reviewing Spec Kit feature work.
  Committed feature contracts follow `requirements/AGENTS.md`.
- Prefer surgical edits. This repository has vendored code, generated code, and
  several CI-specific workflows under `.github/workflows/`.

# Directory

- `yarf/` - Python package, Robot Framework libraries, and internal helpers.
- `tests/` - Robot keyword, platform plugin, and smoke test suites.
- `docs/` - User documentation built with Sphinx and MyST.
- `snap/` - Snap package definition and packaging support.
- `requirements/` - Committed Spec Kit feature contracts.
- `.github/` - CI workflows, actions, and pull request validation.

# Documents

- `.kb/agents.md` - Knowledge-base organization and header rules.
- `.kb/documentation.md` - Documentation scope, location, validation, and maintenance.
- `.kb/pull-requests.md` - Pull request scope, structure, review, and verification.
- `.kb/spec-kit.md` - Spec Kit workflow, contract adoption, and feature delivery.
- `.kb/writing-style.md` - Writing rules for contributor guidance and pull requests.
- `CONTRIBUTING.md` - Development environment, testing, and Snap build instructions.
- `docs/AGENTS.md` - Documentation-specific contributor guidance.
- `docs/CONTRIBUTING.md` - Documentation build and quality-check instructions.
- `requirements/AGENTS.md` - Feature contract format and lifecycle.
