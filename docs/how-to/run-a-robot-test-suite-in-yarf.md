# Run a robot test suite in YARF

This guide will show how to run a robot test suite using YARF.
In general, there are three steps:

1. [Prepare the test suite](#prepare-the-test-suite)
1. [Identify the platform](#identify-the-platform)
1. [Provide the correct variant](#provide-the-correct-variant)
1. [Run the `yarf` command](#run-the-yarf-command)
1. [Debug failing tests](#debug-failing-tests)

## Prepare the test suite

First of all, we need to prepare the test suite. In terms of YARF, a test suite is defined as a directory that at least contains a `.robot` file. For example, we have a directory named `suite`:

```{code-block} bash
---
caption: An example of a simplest test suite
---
suite
└── test.robot
```

This is the simplest test suite YARF will accept. A directory without a `.robot` file will result in an error. There are tag(s) that we support in YARF, for details please visit [Write a Robot File with YARF Tags](./write-a-robot-file-with-yarf-tags.md)

A more comprehensive example of a test suite would be:

```{code-block} bash
---
name: code_snippet_an_example_of_a_more_comprehensive_test_suite
caption: An example of a more comprehensive test suite
---
suite
├── test.robot
├── a1.png
├── sub
│   └── a2.png
└── variants
    └── var
        ├── a1.png
        └── sub
            └── a2.png
```

The `variants` directory contains modified versions of the base templates, organized in sub-directories by specific variations; this will be discussed further in the section [Provide the correct variant](#provide-the-correct-variant).

## Identify the platform

We need to identify the platform that we would like to run to use YARF. The choice is different in different case, for now we are working to support the following platforms:

- Mir: A display server that is suitable for local development and continuous integration. For details please visit [here](https://canonical-mir.readthedocs-hosted.com/stable/)
- VNC: A backend that use QEMU to view and control a virtual machine's graphical desktop. For details of how to start a VNC session please visit [here](using-the-vnc-backend.md)

## Provide the correct variant

A robot task can be executed on different machines and therefore we have variant assets to cater different scenarios. For this, we provide an optional argument `--variant` for the user to specify the variant they are interested to test with and automatically run the test suite with relevant assets in the `variants` directory. The variant is specified by a variant string with the format:

```{code-block} bash
---
caption: Format for the variant string.
---
<attribute1>/<attribute2>/<attribute3>/...
```

Take example on Code Snippet [here](#code_snippet_an_example_of_a_more_comprehensive_test_suite), we can have one variant strings:

1. `var`: When running the test suite, we use `suite/variants/var/a1.png` and `suite/variants/var/sub/a2.png` instead of `suite/a1.png` and `suite/a2.png`.

```{caution}
Do not include the names of asset sub-directories (e.g. `sub` in [this Code Snippet](#code_snippet_an_example_of_a_more_comprehensive_test_suite)) in variant strings because those are part of the suite's assets and are not attributes for us to select different variants. With this, we recommend adding a prefix to the asset sub-directories, like the suite name.
```

When a variant string is provided, we will search for directories that has a name matching any attributes in the variant string in the order of specificity degree. To elaborate, it is the reversed ascending sort by the number of attributes we have in the provided variant string. For example, if we have a variant string `noble/1920/x1080/ubuntu-frame`, we will we searching the directories in the following order:

```{code-block} text
---
caption: Searching order for the variant string 
  `noble/1920/1920x1080/ubuntu-frame`
---
noble/1920/x1080/ubuntu-frame
1920/x1080/ubuntu-frame
noble/1920/x1080
x1080/ubuntu-frame
1920/x1080
noble/1920
ubuntu-frame
x1080
1920
noble
```

We will always take the assets that are discovered in the first occurrence. So for instance if we have an asset name `a5.png` under the directories `noble/1920/x1080` and `x1080`, we will use the one in `noble/1920/x1080` only.

If assets need to be shared between variant directories, symbolic links may be used.

## Run the `yarf` command

To run a test suite named `<suite>` using a given `<platform>`, a `<variant>` and a `<outdir>`, the `yarf` command would be:

```{code-block} bash
---
caption: `yarf` command
---
yarf --variant <variant> --platform <platform> --outdir <outdir> <path-to-test-suite>/suite
```

For information about the option `--outdir`, please refer to the section [Debug failing tests](#debug-failing-tests).
If the `--platform` argument is not specified, then YARF will use Vnc as the platform:

```{code-block} bash
---
caption: `yarf` command without `--platform` option
---
yarf --platform Vnc <path-to-suite>/suite
```

To run with the Mir platform, you need to run a Mir compositor with additional Wayland protocols. You can install the
[`mir-test-tools`](https://snapcraft.io/mir-test-tools) snap and use `mir-test-tools.demo-server`, for example:

```{code-block} bash
---
caption: `yarf` command for Mir
---
export WAYLAND_DISPLAY=wayland-99
export MIR_SERVER_ADD_WAYLAND_EXTENSIONS=zwlr_screencopy_manager_v1:zwlr_virtual_pointer_manager_v1

mir-test-tools.demo-server &  # starts the demo Mir compositor

gnome-calculator &  # start the application

yarf --platform Mir <path-to-suite>/suite
```

You can find out more about Mir at [the Mir documentation site](https://canonical-mir.readthedocs-hosted.com/stable/tutorial/getting-started-with-mir/).

______________________________________________________________________

If you do not have a test suite, you can still use YARF to explore and come up with the robot script you need by using the [Interactive console](interactive-console.md).

### Robot CLI arguments

The Robot Framework CLI provides several additional options, such as the `--variable` argument, which allows you to pass global variables into Robot tests. To ensure compatibility with these features, YARF will pass any option after the `--` separator directly to the Robot Framework parser. The user can view the complete list of supported Robot Framework arguments by running `yarf -- --help`, which will display the Robot Framework argument parser.

```{code-block} bash
---
caption: `yarf` command with Robot-specific argument provided
---
yarf <path-to-suite>/suite -- --variable KEY1:VALUE1 --variable KEY2:VALUE2
```

## Debug failing tests

When developing tests, you will often need more feedback than the command line gives you. `yarf` will output
log files in the `tmp/yarf-outdir` directory. The user can override the target path with the `--outdir` argument:

```{code-block} bash
tmp
└── yarf-outdir
    ├── log.html
    ├── output.xml
    └── report.html
```

You can read about them in [Robot's documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#different-output-files).

When any test fails, YARF adds two important features here:

- For each failing test, it will log the template(s) and the last screenshot.
  This allows you to easily see why the template(s) didn't match. We also recommend that you cut out
  your template(s) from the screenshot provided, so you get them pixel-perfect.
- For the whole suite, it will log a video with all screenshots taken leading up to the failure.
  You'll be able to see what went wrong _before_ the test failed and hopefully identify the problem
  directly from the log file, without having to look at the test run live.
