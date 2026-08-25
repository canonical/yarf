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
- **Execution flow.** Install workflow dependencies, install YARF, start the
  platform, launch the app under test, run YARF, upload the output directory as
  an artifact, write a job summary, and propagate YARF's pass/fail to the job.
- **Source install only, no snap option.** The action builds YARF from source
  into a virtual environment on the runner. That lets it run any git ref, which
  the snap's channels cannot express, and keeps compatibility with platform
  plugins, which are ordinary Python packages and are not necessarily snapped.
- **Version pinning follows the action.** `yarf-ref` defaults to the ref the
  action itself was called at, so `yarf-test@3.16.0` runs YARF 3.16.0, and the
  source is fetched from the repository the action came from, which keeps forks
  working. Workflows in this repository pass `yarf-path` instead, reusing the
  checkout they already have.
- **Platform providers.** The `stock` provider starts a virtual Mir compositor
  (no graphics hardware required) with `wayvnc` in front of it, which serves
  the `Mir` and `Vnc` platforms alike; `Vnc` is a protocol rather than a
  platform of its own. Everything else is a `custom` provider, driven by
  consumer-supplied `platform-setup-command`, `platform-ready-command`, and
  `platform-teardown-command`. Driving a whole OS, for example under QEMU,
  involves too many variables to bake into the action; it belongs in a native
  YARF platform and is served by `custom` until then.
- **Output location.** The action passes `--outdir` itself and exposes the
  directory via the `output-dir` output, so downstream steps and the artifact
  upload do not hardcode a path.

## Consequences

- Consumers get a one-step way to run YARF in GitHub Actions on their own Ubuntu
  runners, with results surfaced as an artifact and job summary.
- Bootstrapping stays outside the snap, avoiding the confinement issue that made
  in-snap bootstrapping infeasible.
- The action must stay in sync with YARF's CLI and output conventions. Rather
  than adding a dedicated self-test workflow, this repository's own workflows
  ([`yarf.yaml`](../.github/workflows/yarf.yaml) and
  [`platform-plugin-test.yaml`](../.github/workflows/platform-plugin-test.yaml))
  run through the action, so both providers are exercised on every change.
- Testing on hardware (e.g. via Zapper/Testflinger) needs additional operations
  such as credentials and plugins and is intentionally out of scope here; it is
  expected to be offered as a separate service.
