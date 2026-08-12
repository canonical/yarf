# 0001 - YARF GitHub Action for running tests in CI

- Status: Accepted
- Date: 2026-08-12

## Context

YARF runs as a snap-confined visual test runner. To run a suite, something has
to bring up a platform (a Wayland compositor such as Mir, or a VNC endpoint) and
start the application/OS under test before YARF drives and asserts against it.

We explored building this bootstrapping inside YARF itself. That turned out not
to be workable: snap confinement would require granting YARF permission to
control arbitrary other applications, which is not a boundary we want the snap
to cross. As a result, the setup work needs to live outside the snap.

Consumers still want a simple, reproducible way to run YARF visual tests in
their own CI without hand-rolling compositor startup, dependency installation,
and result handling in every repository.

## Decision

Provide a reusable, composite GitHub Action at
[`.github/actions/yarf-test`](../.github/actions/yarf-test/action.yaml) that
consumers invoke with a single `uses:` step.

- **Thin orchestration, testable scripts.** `action.yaml` only wires steps
  together; the real logic lives in small, single-responsibility bash scripts
  under `scripts/` (`install-deps.sh`, `install-yarf.sh`, `start-platform.sh`,
  `run-yarf.sh`), each runnable standalone for testing.
- **Execution flow.** Install workflow dependencies, install YARF (from a snap
  channel by default, or built from a git ref via `yarf-ref`), start the
  platform, launch the app under test, run YARF, upload the output directory as
  an artifact, write a job summary, and propagate YARF's pass/fail to the job.
- **Platform providers.** `Mir` and `Vnc` get a built-in virtual Mir compositor
  (no graphics hardware required, plus `wayvnc` for VNC). Any other platform is
  treated as a `custom` provider, driven by consumer-supplied
  `platform-setup-command`, `platform-ready-command`, and
  `platform-teardown-command`.
- **Output location.** The YARF output directory differs by install mode
  (`~/snap/yarf/common/yarf-outdir/` for the snap, `$TMPDIR/yarf-outdir` for a
  source install). The action resolves this and exposes it via the `output-dir`
  output so downstream steps and artifact upload do not hardcode it.

## Consequences

- Consumers get a one-step way to run YARF in GitHub Actions on their own Ubuntu
  runners, with results surfaced as an artifact and job summary.
- Bootstrapping stays outside the snap, avoiding the confinement issue that made
  in-snap bootstrapping infeasible.
- The action must stay in sync with YARF's CLI and output conventions; a
  self-test workflow ([`test-yarf-action.yaml`](../.github/workflows/test-yarf-action.yaml))
  exercises it against the canary suite on the built-in providers.
- Testing on hardware (e.g. via Zapper/Testflinger) needs additional operations
  such as credentials and plugins and is intentionally out of scope here; it is
  expected to be offered as a separate service.
