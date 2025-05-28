# Yet Another Robot Framework (YARF)

[![Snapcraft][snapcraft-badge]][snapcraft-site]
[![Documentation status][rtd-badge]][rtd-latest]
[![uv status][uv-badge]][uv-site]
[![Ruff status][ruff-badge]][ruff-site]

**YARF** is a tool built upon the [Robot Framework]
that allows developers to build complex visual test scenarios and bootstrap them
locally, and then work towards automated runs in continuous integration (CI) and
use of platforms/fixtures like [Mir] and VNC with minimal effort.

## Basic Usage

To start YARF in interactive mode, simply run:

```shell
yarf --platform {Mir,Vnc}
```

For more specific use-cases, refer to the [YARF how-to guides][how-to].

## Installation

YARF is available on all major Linux distributions.

On snap-ready systems, you can install it on the command-line with:

```shell
sudo snap install yarf
```

## Documentation

The YARF docs provide guidance and learning material about the robot libraries,
resources, metadata, use-cases, and much more:

- [YARF documentation on ReadTheDocs][rtd-latest]

## Community and Support

You can report any issues, bugs, or feature requests on the project's
[GitHub repository][github].

## Contribute to YARF

<!-- TODO: YARF is open source. Contributions are welcome. -->

If you are interested, start with the [contribution guide].

## License and Copyright

<!-- TODO: YARF is released under the [TBD license](COPYING). -->

© 2025 Canonical Ltd.

[contribution guide]: ./CONTRIBUTING.md
[github]: https://github.com/canonical/yarf
[how-to]: https://canonical-yarf.readthedocs-hosted.com/en/latest/how-to/
[mir]: https://github.com/canonical/mir
[robot framework]: https://robotframework.org/
[rtd-badge]: https://readthedocs.com/projects/canonical-yarf/badge/?version=latest
[rtd-latest]: https://canonical-yarf.readthedocs-hosted.com/en/latest/
[ruff-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff-site]: https://github.com/astral-sh/ruff
[snapcraft-badge]: https://snapcraft.io/yarf/badge.svg
[snapcraft-site]: https://snapcraft.io/yarf
[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
[uv-site]: https://github.com/astral-sh/uv
