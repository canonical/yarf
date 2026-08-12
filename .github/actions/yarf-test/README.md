# YARF test action

Run [YARF](https://github.com/canonical/yarf) visual tests in your own CI with a
single `uses:` step. The action installs the necessary dependencies, starts a
platform (built-in Mir/Vnc or a custom provider), starts the app/OS under test
via a command you provide, runs YARF against a test suite, and surfaces the YARF
output as an uploaded artifact and job summary — failing the job when tests
fail.

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
          yarf-channel: latest/stable
```

### Custom platform provider

Use `platform-provider: custom` when the platform is not the built-in Mir/Vnc
compositor (for example a YARF platform plugin). Install and start the platform
with `platform-setup-command`, optionally block until it is ready with
`platform-ready-command`, and clean up with `platform-teardown-command`.

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
            sudo snap install my-yarf-plugin --dangerous
            sudo snap connect my-yarf-plugin:platform-plugins yarf:platform-plugins
            ./ci/start-my-platform.sh
```

## Inputs

| Input                       | Required | Default        | Description                                                                                     |
| --------------------------- | -------- | -------------- | ----------------------------------------------------------------------------------------------- |
| `platform`                  | yes      | —              | Value passed to `yarf --platform`.                                                              |
| `platform-provider`         | no       | `Mir`          | Platform YARF starts with: `Mir`, `Vnc`, or `custom`.                                           |
| `platform-setup-command`    | no       | `""`           | Command(s) to start the platform when `platform-provider` is `custom`.                          |
| `platform-ready-command`    | no       | `""`           | Command(s) that block until a custom platform is ready.                                          |
| `platform-teardown-command` | no       | `""`           | Command(s) to tear down a custom platform after the run.                                         |
| `test-path`                 | yes      | —              | Path (in the consumer's checkout) to the YARF test suite to run.                                |
| `launch-command`            | no       | `""`           | Command to start the app/OS under test, just before running YARF. Skipped when empty.           |
| `yarf-channel`              | no       | `latest/stable`| Snap channel to install YARF from when `yarf-ref` is unset.                                      |
| `yarf-ref`                  | no       | `""`           | Git ref (branch/tag/SHA) to build and install YARF from source instead of the snap.             |
| `yarf-args`                 | no       | `""`           | Extra yarf options placed before the test path (e.g. `--output-format TestSubmissionSchema`).   |
| `robotframework-args`       | no       | `""`           | Extra args appended after `--` to the yarf invocation (e.g. `--suite foo`).                     |
| `display-size`              | no       | `1280x1024`    | Virtual output resolution for the built-in platforms.                                           |
| `artifact-name`             | no       | `yarf-output`  | Name for the uploaded results artifact.                                                          |
| `upload-artifact`           | no       | `true`         | Whether to upload the YARF output dir as an artifact.                                            |

## Outputs

| Output       | Description                                |
| ------------ | ------------------------------------------ |
| `output-dir` | Absolute path to YARF's output directory.  |
| `result`     | `passed` or `failed`.                      |

The output directory differs by install mode: the snap writes to
`~/snap/yarf/common/yarf-outdir/`, while a source install writes to
`$TMPDIR/yarf-outdir`. The action resolves the correct path based on the install
mode and exposes it via `output-dir` so downstream steps and the artifact upload
do not hardcode it.
