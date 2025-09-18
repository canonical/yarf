# YARF-Example

**YARF-Example** is a example plugin library for YARF.
For more information about YARF, please visit [here](https://github.com/canonical/yarf).
In this `README` we will go through the contents on this plugin.

## Structure of the plugin

```{bash}
yarf-example-plugin
├── README.md
├── .gitignore
├── pyproject.toml
├── snap
|   ├── hooks
|   |   └── configure
|   └── snapcraft.yaml
└── src
    └── yarf_plugin_example
        ├── __init__.py
        ├── Hid.py
        └── VideoInput.py
```

> [!NOTE]
> All YARF platform plugins’ package directory name has to be prefixed by `yarf_plugin_`.

1. `src`: Contains the source code for the example plugin.

   - `__init__.py`: Contains the `Example` class, which implements the necessary functions of YARF `PlatformBase` class for this example plugin.
   - `Hid.py`: Contains the `Hid` class, which implements the necessary functions of YARF `HidBase` class for this example plugin.
   - `VideoInput.py`: Contains the `VideoInput` class, which implements the necessary functions of YARF `VideoInputBase` class for this example plugin.

1. `snap`: Contains the snapcraft YAML file, which describes the information and necessary items and steps to build this example plugin as a snap. The file `snap/hooks/configure` copies the example plugin to `$SNAP_COMMON/platform_plugins/` directory, this location will be shared with YARF so that YARF can recognize this platform.

1. `pyproject.toml`: Contains the information for this plugin, along with the build system and dependencies.

1. `.gitignore`: Contains file patterns to ignore when commit.

For details, please visit teach of these files.

## Installation

There are two scenarios:

1. Running YARF from source. In this case we will be installing the `yarf-example-plugin` using `pip`:

   ```
   pip install examples/yarf-example-plugin
   ```

1. Running YARF snap. In this case, we need to first get the `yarf-example-plugin` snap. After that, we connect the `platform-plugins` interface with YARF and onboard the plugin:

   ```
   sudo snap connect yarf-example-plugin:platform-plugins yarf:platform-plugins
   sudo snap run yarf-example-plugin.onboard-plugin
   ```

After installing the plugin, we will be able to use the `Example` plugin as if it is a usual platform. For example:

```
snap run yarf --platform Example <path-to-suite>
```
