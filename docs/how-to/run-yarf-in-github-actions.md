# Run YARF in GitHub Actions

YARF ships a composite GitHub action, `yarf-test`, that runs a test suite in a
workflow with a single `uses:` step. The action installs the dependencies,
installs YARF into a virtual environment, starts a platform, starts the
application under test, runs the suite, and uploads the YARF output as an
artifact. The job fails when the suite fails.

## Before you start

The action expects the following:

- An Ubuntu runner.
- A checkout of the repository that holds the suite, because `test-path` is
  read from the workspace. Run `actions/checkout` before the action.
- Git LFS enabled in the checkout (`lfs: true`) when the suite stores its
  reference images in Git LFS.

## Run a suite on the stock platform

The `stock` provider starts a headless Mir compositor, so no graphics hardware
is needed, and puts `wayvnc` in front of it. It therefore serves both the `Mir`
and the `Vnc` platform.

```{code-block} yaml
---
caption: A workflow that runs a suite against a locally started application
---
jobs:
  visual-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true
      - uses: canonical/yarf/.github/actions/yarf-test@main
        with:
          platform: Mir
          test-path: tests/visual
          launch-command: dbus-run-session -- my-app
```

Leave `launch-command` empty when the suite starts the application itself, for
example in a `Suite Setup`.

Install the packages that the suite drives, such as the application under test,
in a step before the action. The action only installs the compositor and YARF
itself.

## Run a suite on a platform plugin

Set `platform-provider` to `custom` when the platform is not the stock
compositor, for example a platform plugin. See
{doc}`./platform-plugins` for how to write one. This provider requires three
commands:

- `platform-setup-command` installs and starts the platform.
- `platform-ready-command` blocks until the platform is ready.
- `platform-teardown-command` cleans up after the run.

The action installs YARF into a virtual environment and puts it on `PATH`, so
install the plugin from the setup command without naming an interpreter. YARF
discovers plugins in the `site-packages` of the interpreter it runs on, and this
keeps both in the same environment.

```{code-block} yaml
---
caption: A workflow that runs a suite against a platform plugin
---
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
            pip install ./my-yarf-plugin
            ./ci/start-my-platform.sh
          platform-ready-command: yarf --platform MyPlatform --help
          platform-teardown-command: pip uninstall --yes my-yarf-plugin
```

A readiness command such as `yarf --platform MyPlatform --help` fails when the
plugin was not discovered, which reports a broken installation before the suite
runs.

## Test a virtual machine

The `Vnc` platform is a client: it connects to `VNC_HOST:5900+VNC_PORT` and does
not depend on what serves that port. To drive a whole operating system, start a
virtual machine that exposes a display with the `custom` provider and keep
`platform: Vnc`. See {doc}`./using-the-vnc-backend` for the QEMU arguments and
the environment variables.

```{code-block} yaml
---
caption: A workflow that runs a suite against a virtual machine
---
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

The readiness command above proves only that QEMU listens on the port, not that
the guest finished booting. Let the suite wait for the first `Match` instead.

## Select what YARF runs

The following inputs shape the YARF invocation:

| Input                 | Effect                                                                         |
| --------------------- | ------------------------------------------------------------------------------ |
| `yarf-args`           | Options placed before the test path, such as `--variant`.                      |
| `robotframework-args` | Arguments appended after `--`, such as `--suite` or `--test`.                  |
| `yarf-ref`            | Git ref to install YARF from. Defaults to the ref the action was called at.    |
| `yarf-path`           | Path to a YARF source tree to install instead. Takes priority over `yarf-ref`. |

```{code-block} yaml
---
caption: Running a single suite from a larger test path
---
      - uses: canonical/yarf/.github/actions/yarf-test@main
        with:
          platform: Mir
          test-path: tests/visual
          robotframework-args: --suite login
```

## Use the results

The action always uploads the YARF output directory as an artifact, named by
`artifact-name`, and writes a short summary to the job summary page. It also
exposes two outputs:

- `result` is `passed` or `failed`.
- `output-dir` is the absolute path of the YARF output directory.

The action passes `--outdir` to YARF itself, so an `--outdir` in `yarf-args` has
no effect. Reference `output-dir` in later steps instead of a fixed path.

```{code-block} yaml
---
caption: Validating the test submission schema after a run
---
      - uses: canonical/yarf/.github/actions/yarf-test@main
        id: yarf
        with:
          platform: Mir
          test-path: tests/canary_test
          yarf-args: --output-format TestSubmissionSchema
      - env:
          OUTPUT_DIR: ${{ steps.yarf.outputs.output-dir }}
        run: check-jsonschema --schemafile "$SCHEMA" "${OUTPUT_DIR}/TestSubmissionSchema_output.json"
```

## Troubleshoot a run

- Inputs are validated before anything is installed, so a workflow with invalid
  inputs fails on the first step with every problem listed at once.
- Download the uploaded artifact and open `log.html` to see the screenshots
  that YARF compared.
- Reference images capture the theme and window decorations of the machine
  that recorded them. Install the same packages in the workflow, otherwise a
  suite can fail on a difference such as a missing title bar button.
