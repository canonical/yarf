# AGENTS.md

Fast repo guide for coding agents. Keep this file short; use `CONTRIBUTING.md`
and `docs/CONTRIBUTING.md` for full contributor docs.

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

## Mir / Wayland caveat

The Mir platform uses `os.memfd_create`, which is missing from uv-managed
Python builds. If you need to run or test Mir/Wayland code, create the venv
with system Python (this matches the command in `CONTRIBUTING.md`):

```bash
uv --no-managed-python venv --system-site-packages
uv sync
```

## Repo-specific guardrails

- Line length is **79**.
- Public Python modules generally need module docstrings (`D100` is enforced).
- Docstrings use Google style; `docformatter` is configured with
  `--pre-summary-newline`.
- `mypy` runs with `--check-untyped-defs`.
- Coverage for `yarf` is gated at **100%** in tox.
- To exclude a keyword from keyword coverage, use `yarf: nocoverage` and explain
  why.
- Avoid editing `yarf/vendor/` and `yarf/lib/wayland/protocols/` unless the task
  is specifically about vendored/generated code.

## Easy-to-miss checks

- If you change files in `yarf/rf_libraries/**/*.py`, pre-commit also checks that
  generated library docs under `docs/` are up to date via
  `make -C docs libdoc-convert`.
- Docs-only checks such as spelling/link/inclusive-language/style/accessibility
  exist in prek manual hooks; run them when touching `docs/`.

## Before making broad changes

- Read `CONTRIBUTING.md` if the change affects packaging, Snap builds, docs, or
  keyword coverage policy.
- Prefer surgical edits; this repo has vendored code, generated code, and several
  CI-specific workflows under `.github/workflows/`.
