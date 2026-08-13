# YARF test action

Run [YARF](https://github.com/canonical/yarf) visual tests in your own CI with a
single `uses:` step. The action installs the necessary dependencies, installs
YARF from source at `yarf-ref`, starts a platform (built-in Mir/Vnc or a custom
provider), starts the app/OS under test via a command you provide, runs YARF
against a test suite, and surfaces the YARF output as an uploaded artifact and
job summary — failing the job when tests fail.

The caller must run `actions/checkout` first so the test suite is available.

## Usage

### Built-in platform (Mir/Vnc)

```yaml
jobs:
  visual-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: canonical/yarf/.github/actions/yarf-test@main
        with:
          platform: Mir
          platform-provider: Mir
          test-path: tests/visual
          launch-command: dbus-run-session -- my-app
```

### Custom platform provider

Use `platform-provider: custom` when the platform is not the built-in Mir/Vnc
compositor (for example a YARF platform plugin). Install and start the platform
with `platform-setup-command`, block until it is ready with
`platform-ready-command`, and clean up with `platform-teardown-command`; all
three are required for this provider.

When the plugin is installed with `pip`, set `python-version`. YARF only
discovers plugins in `site-packages`, and on the runner's system Python `pip`
falls back to a user install that YARF does not scan, so it is required for this
provider.

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
          python-version: "3.12"
          test-path: tests/visual
          platform-setup-command: |
            python3 -m pip install --break-system-packages ./my-yarf-plugin
            ./ci/start-my-platform.sh
          platform-ready-command: yarf --platform MyPlatform --help
          platform-teardown-command: python3 -m pip uninstall --yes my-yarf-plugin
```

## Inputs

Inputs are validated before anything is installed, so a misconfigured workflow
fails immediately with every problem listed at once. `platform-provider` is
accepted in any casing.

| Input                       | Required          | Default         | Description                                                                                   |
| --------------------------- | ----------------- | --------------- | --------------------------------------------------------------------------------------------- |
| `platform`                  | yes               | —               | Value passed to `yarf --platform`.                                                            |
| `platform-provider`         | no                | `Mir`           | Platform YARF starts with: `Mir`, `Vnc`, or `custom`.                                         |
| `platform-setup-command`    | for `custom`      | `""`            | Command(s) to start the platform when `platform-provider` is `custom`.                        |
| `platform-ready-command`    | for `custom`      | `""`            | Command(s) that block until a custom platform is ready.                                       |
| `platform-teardown-command` | for `custom`      | `""`            | Command(s) to tear down a custom platform after the run.                                      |
| `python-version`            | for `custom`      | `""`            | Python version to set up before installing YARF. Needed for pip-installed plugins.            |
| `test-path`                 | yes               | —               | Path (in the consumer's checkout) to the YARF test suite to run.                              |
| `launch-command`            | yes               | `""`            | Command to start the app/OS under test, just before running YARF. Leave empty when the suite starts the app itself. |
| `yarf-ref`                  | no                | `main`          | Git ref (branch/tag/SHA) to build and install YARF from.                                      |
| `yarf-args`                 | no                | `""`            | Extra yarf options placed before the test path (e.g. `--output-format TestSubmissionSchema`). |
| `robotframework-args`       | no                | `""`            | Extra args appended after `--` to the yarf invocation (e.g. `--suite foo`).                   |
| `display-size`              | no                | `1280x1024`     | Virtual output resolution for the built-in platforms.                                         |
| `artifact-name`             | no                | `yarf-output`   | Name for the uploaded results artifact.                                                       |
| `upload-artifact`           | no                | `true`          | Whether to upload the YARF output dir as an artifact.                                         |

## Outputs

| Output       | Description                               |
| ------------ | ----------------------------------------- |
| `output-dir` | Absolute path to YARF's output directory. |
| `result`     | `passed` or `failed`.                     |

The output directory is `$TMPDIR/yarf-outdir`. The action exposes it via
`output-dir` so downstream steps and the artifact upload do not hardcode it.
Passing an explicit `--outdir <path>` through `yarf-args` takes precedence and
is reflected in `output-dir`.
