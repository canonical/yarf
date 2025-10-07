# Platform plugins

YARF allows platforms to be added as plugins. In this guide, we will walk through how to write a platform plugin and how to make it available in YARF.

## Writing a platform plugin

In YARF, all platforms are delivered as a package and must implement the `PlatformBase` class in an `__init__.py`, this extends to the platform plugins. For example:

```{code-block} bash
---
caption: An example of a simplest platform plugin module named Platform A
---
yarf-platform-A
├── pyproject.toml
└── src
    └── yarf_plugin_platform_A
        ├── tests
        └── __init__.py
```

An example of `pyproject.toml` is:

```{code-block} toml
---
caption: An example of `pyproject.toml`
---
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "yarf-platform-A"
version = "0.0.1"
description = "Platform A plugin library for YARF."
authors = [
    { name = "...", email = "..." }
]
readme = "README.md"
requires-python = ">=3.10,<3.13"
dependencies = [
    "yarf @ git+ssh://git@github.com/canonical/yarf.git@x.y.z",
    "...",
]

[tool.hatch.build]
packages = ["src/yarf_plugin_platform_A"]

...
```

In the `__init__.py`:

```{code-block} python
---
caption: `__init__.py` for Platform A
---
from yarf.rf_libraries.libraries import PlatformBase


class PlatformA(PlatformBase):
    def __init__(self) -> None:
        pass

    @staticmethod
    def get_pkg_path() -> str:
        return str(Path(__file__).parent)
```

By implementing the `PlatformBase` class, Platform A will be auto-registered to YARF's supported platforms when imported.

```{note}
All YARF platform plugins' package directory name has to be prefixed by `yarf_plugin_`.
```

We can also make use of the base classes in `yarf/rf_libraries/libraries` to implement classes like `VideoInput` and `Hid` if we found these useful for Platform A. If we choose to do so, we will have a module structured like:

```{code-block} bash
---
caption: An example of plugin Platform A with Hid and VideoInput
---
yarf-platform-A
├── pyproject.toml
└── src
    └── yarf_plugin_platform_A
        ├── tests
        ├── __init__.py
        ├── Hid.py
        └── VideoInput.py
```

Take example of `Hid.py`, we can have something like:

```{code-block} python
---
caption: An example of Hid implementation in Platform A
---
from yarf.rf_libraries.libraries.hid_base import HidBase
from yarf_plugin_platform_A import PlatformA


@library
class Hid(HidBase):
    """
    Provides robot interface for HID interactions with a running Platform A
    server.
    """

    def __init__(self) -> None:
        super().__init__()
        self.platform = PlatformA()
        self.curr_x = 0
        self.curr_y = 0

    ...
```

## Managing plugin platforms in YARF

There are two ways to manage platform plugins in YARF:

1. `pip`: We can install and delete the plugin to YARF using `pip`, for example:

   ```{code-block} bash
   pip install /path/to/your/plugin/directory/platform_A
   ```

   ```{code-block} bash
   pip uninstall yarf_plugin_platform_A
   ```

1. Snap: The YARF snap provides a `platform-plugins` interface to receive a plugin. In the plugin snap, we can add a plug so that the snap can share the plugin's location to YARF. For example:

   ```{code-block} yaml
   ---
   caption: An example plug `write-yarf-platform-plugins` that shares a plugin
   ---
   plugs:
       write-yarf-platform-plugins:
       interface: content
       target: $SNAP_COMMON/platform-to-plug
   ```

   Then we can connect the snap with the plugin with YARF:

   ```{code-block} bash
   sudo snap connect snap-with-plugin:write-yarf-platform-plugins yarf:platform-plugins
   ```

   ```{tip}
   We recommend writing interface hooks for easy onboarding and removal of the plugin.
   For details on how to write interface hooks, please visit [here](https://snapcraft.io/docs/interface-hooks).
   ```

   After that, we will need to move `yarf_plugin_platform_A` to `$SNAP_COMMON/platform-to-plug`.

A working example of a platform plugin can be found in `examples/yarf-example-plugin` of the YARF repository.
