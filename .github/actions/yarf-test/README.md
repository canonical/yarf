# YARF test action

Run [YARF](https://github.com/canonical/yarf) visual tests in your own CI with a
single `uses:` step. The action installs the necessary dependencies, installs
YARF from source into a `uv` venv, starts a platform (the stock Mir + `wayvnc`
compositor or a custom provider), starts the app/OS under test via a command you
provide, runs YARF against a test suite, and surfaces the YARF output as an
uploaded artifact and job summary — failing the job when tests fail.

YARF is built from the ref the action itself was called at, so
`yarf-test@3.16.0` runs YARF 3.16.0. Pin a release tag to keep runs
reproducible; `@main` follows the latest development state. Override the YARF
version independently with `yarf-ref`, or point `yarf-path` at a source tree you
already checked out.

```yaml
# Pinned: installs YARF 3.16.0.
- uses: canonical/yarf/.github/actions/yarf-test@3.16.0

# Unpinned: installs YARF from main.
- uses: canonical/yarf/.github/actions/yarf-test@main
```

The venv is put on `PATH` and exported as `VIRTUAL_ENV`, and it is seeded with
`pip`, so both `pip install` and `uv pip install` in your own commands and later
steps target the same environment as YARF. Packages already installed on the
runner stay importable, as the venv is created with `--system-site-packages`.

The caller must run `actions/checkout` first so the test suite is available.

## Usage

### Stock platform

The stock provider starts a headless Mir compositor with `wayvnc` in front of
it, so it serves both the `Mir` and the `Vnc` platform. It does not boot an
operating system.

```yaml
jobs:
  visual-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: canonical/yarf/.github/actions/yarf-test@main
        with:
          platform: Mir
          test-path: tests/visual
          launch-command: dbus-run-session -- my-app
```

### Custom platform provider

Use `platform-provider: custom` when the platform is not the stock compositor
(for example a YARF platform plugin). Install and start the platform
with `platform-setup-command`, block until it is ready with
`platform-ready-command`, and clean up with `platform-teardown-command`; all
three are required for this provider.

When the plugin is installed with `pip`, install it into the venv the action
creates for YARF (`uv pip install …` picks it up automatically), since YARF only
discovers plugins in the `site-packages` of the interpreter it runs on.

```yaml
jobs:
  visual-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: canonical/yarf/.github/actions/yarf-test@main
        with:
          platform: MyPlatform
          platform-provider: custom
          test-path: tests/visual
          platform-setup-command: |
            uv pip install ./my-yarf-plugin
            ./ci/start-my-platform.sh
          platform-ready-command: yarf --platform MyPlatform --help
          platform-teardown-command: uv pip uninstall my-yarf-plugin
```

### Testing a virtual machine over VNC

YARF's `Vnc` platform is a VNC client: it connects to `VNC_HOST:5900+VNC_PORT`
and does not care what serves that port. To drive a whole OS instead of a
compositor, start a VM that exposes a VNC display with the `custom` provider and
keep `platform: Vnc`. See
[Using the VNC backend](../../../docs/how-to/using-the-vnc-backend.md) for the
QEMU arguments and the `VNC_HOST`/`VNC_PORT` variables.

```yaml
jobs:
  vm-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: canonical/yarf/.github/actions/yarf-test@main
        with:
          platform: Vnc
          platform-provider: custom
          test-path: tests/vm
          platform-setup-command: |
            qemu-system-x86_64 -accel kvm -m 2048 -smp 2 \
              -drive file=/tmp/vm.img,format=qcow2 -vnc :0 -daemonize
          platform-ready-command: timeout 120 bash -c 'until nc -z localhost 5900; do sleep 2; done'
          platform-teardown-command: "pkill -f '[q]emu-system-x86_64' || true"
```

The readiness command only proves QEMU is listening, not that the guest booted;
let the suite wait for the first `Match`. `display-size` is unused here, as the
resolution comes from the guest.

## Inputs

Inputs are validated before anything is installed, so a misconfigured workflow
fails immediately with every problem listed at once. `platform-provider` is
accepted in any casing.

| Input                       | Required     | Default       | Description                                                                                                         |
| --------------------------- | ------------ | ------------- | ------------------------------------------------------------------------------------------------------------------- |
| `platform`                  | yes          | —             | Value passed to `yarf --platform`.                                                                                  |
| `platform-provider`         | no           | `stock`       | Platform YARF starts with: `stock` or `custom`.                                                                     |
| `platform-setup-command`    | for `custom` | `""`          | Command(s) to start the platform when `platform-provider` is `custom`.                                              |
| `platform-ready-command`    | for `custom` | `""`          | Command(s) that block until a custom platform is ready.                                                             |
| `platform-teardown-command` | for `custom` | `""`          | Command(s) to tear down a custom platform after the run.                                                            |
| `test-path`                 | yes          | —             | Path (in the consumer's checkout) to the YARF test suite to run.                                                    |
| `launch-command`            | no           | `""`          | Command to start the app/OS under test, just before running YARF. Leave empty when the suite starts the app itself. |
| `yarf-ref`                  | no           | action's ref  | Git ref (branch/tag/SHA) to build and install YARF from.                                                            |
| `yarf-path`                 | no           | `""`          | Path to a YARF source tree to install instead of fetching one. Takes priority over `yarf-ref`.                      |
| `yarf-args`                 | no           | `""`          | Extra yarf options placed before the test path (e.g. `--output-format TestSubmissionSchema`).                       |
| `robotframework-args`       | no           | `""`          | Extra args appended after `--` to the yarf invocation (e.g. `--suite foo`).                                         |
| `yarf-command-suffix`       | no           | `""`          | Shell text appended to the yarf invocation (e.g. `2> ~/wayland.trace`). Evaluated by bash.                          |
| `display-size`              | no           | `1280x1024`   | Virtual output resolution for the stock platform.                                                                   |
| `artifact-name`             | no           | `yarf-output` | Name for the uploaded results artifact.                                                                             |
| `upload-artifact`           | no           | `true`        | Whether to upload the YARF output dir as an artifact.                                                               |

## Outputs

| Output       | Description                               |
| ------------ | ----------------------------------------- |
| `output-dir` | Absolute path to YARF's output directory. |
| `result`     | `passed` or `failed`.                     |

The output directory is `$TMPDIR/yarf-outdir`. The action passes it to YARF as
`--outdir` and exposes it via `output-dir`, so downstream steps and the artifact
upload do not hardcode it. An `--outdir` in `yarf-args` is therefore ignored.
