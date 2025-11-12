# Yet Another Robot Framework (YARF)

This document provides the information needed to contribute to YARF and its documentation.

## Requirements

This repository requires the following dependencies:

- [Python 3.12][python]
- [`uv`][uv]

## Set up your development environment

### Install YARF with dependencies on a virtual environment

First, install a couple of deb package dependencies:

```shell
sudo apt install -y build-essential libxkbcommon-dev tesseract-ocr python3-tk
```

> [!NOTE]
> The package `python3-tk` is optional when running from source.

We can install YARF along with the dependencies specified in
`pyproject.toml` in the virtual environment using the command:

```shell
uv --no-managed-python venv --system-site-packages
uv sync
```

Optionally, enable pre-commit checks, so your contribution will pass all the checks
we run on the code:

```shell
uv run prek install
```

We can start working on the repository here.

## Build the Snap Package

YARF is distributed as a [Snap package][snap].

Install [`snapcraft`][snapcraft]:

```shell
sudo snap install --classic snapcraft
```

Then you can build the Snap package by running `snapcraft`:

```shell
snapcraft pack
```

Then you should see a `yarf_<version>_<architecture>.snap` under
the repository directory. To install it use the command:

```shell
sudo snap install --dangerous yarf_{version}_{architecture}.snap
```

## Tests

[`tox`][tox] is used to automate quality control tasks in YARF, including:

- Linting and formatting ([`ruff`][ruff])
- Unit test with coverage ([`pytest`][pytest])

To run the above quality control tasks, simply execute the command under
the repository directory:

```shell
uv run tox
```

## Documentation

The YARF documentation is maintained under the [`docs/`](./docs/) subdirectory.
To submit changes to the documentation, please read the [documentation contributing guide](./docs/CONTRIBUTING.md).

[pytest]: https://docs.pytest.org/en/stable/
[python]: https://www.python.org/downloads/release/python-3125/
[ruff]: https://docs.astral.sh/ruff/
[snap]: https://snapcraft.io/yarf
[snapcraft]: https://snapcraft.io/snapcraft
[tox]: https://tox.wiki/
[uv]: https://docs.astral.sh/uv/
