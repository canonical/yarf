# Yet Another Robot Framework (YARF)

YARF is a tool built upon the [Robot Framework](https://robotframework.org/)
that allows developers to build complex visual test scenarios and bootstrap them
locally, and then work towards automated runs in continuous integration (CI) and
use of platforms/fixtures like [Example](https://github.com/canonical/Example)
with minimal effort. This reduces turnaround times without sacrificing quality
and trust in the test results.

## Table of Contents

- [Installation Guide](#installation-guide)
- [Running YARF](#running-yarf)
- [Testing](#testing)

<a name="installation-guide"></a>

## Installation Guide

### Requirements

This repository requires the following dependencies

- [Python 3.12](https://www.python.org/downloads/release/python-3125/)
- [uv](https://docs.astral.sh/uv/)
- [Snapcraft](https://snapcraft.io/docs/installing-snapcraft)

### Installing for contribution

1. **Installing YARF with dependencies on a virtual environment**

   First, install a couple of deb package dependencies:

   ```
   sudo apt install -y clang libxkbcommon-dev tesseract-ocr python3-tk
   ```

   > [!NOTE]
   > The package `python3-tk` is optional when running from source.

   We can install YARF along with the dependencies specified in
   `pyproject.toml` in the virtual environment using the command:

   ```
   uv sync
   uv pip install .[develop]
   ```

   After that, we enter the virtual environment:

   ```
   . .venv/bin/activate
   ```

   Optionally, enable pre-commit checks, so your contribution will pass all the checks
   we run on the code:

   ```
   uv tool run --from 'pre-commit<4.0.0' pre-commit install
   ```

   We can start working on the repository here.

1. **Leaving the virtual environment**

   When we finish working with the repository and leaving the virtual environment,
   we can execute:

   ```
   deactivate
   ```

### Installing as a Snap package

1. **Make a Snap package**

   YARF can also be delivered using Snap, to create a Snap package:

   ```
   snapcraft
   ```

1. **Install the Snap package**

   Then we should see a `yarf_<version>_<architecture>.snap` under
   the repository directory. To install it use the command:

   ```
   sudo snap install yarf_{version}_{architecture}.snap --dangerous
   ```

<a name="running-yarf"></a>

## Running YARF

Please run `yarf --help` to learn more about the usage.

<a name="testing"></a>

## Testing

[tox](https://tox.wiki/) is used to automate quality control tasks in YARF,
including:

- Linting and formatting ([ruff](https://docs.astral.sh/ruff/))
- Unit test with coverage ([pytest](https://docs.pytest.org/en/stable/))

To run the above quality control tasks, simply execute the command under
the repository directory:

```
uv tool run tox
```
