# Writing a test suite

```{note}
**Prerequisites**

Before starting this tutorial, make sure you’ve completed:
- [Getting Started][getting-started]

If you’re already comfortable with these topics, feel free to continue.
```

`simple-counter` is an example application (located under `examples/yarf-example-simple-counter` of this repository) that we use in our YARF tutorials to demonstrate YARF's functionalities.

In this tutorial, we will create an automated test suite for the `simple-counter` application to verify that our features work as expected using YARF with Mir. Let's say we have just developed the following buttons:

1. `-`: The count displayed will minus one.
1. `+`: The count displayed will plus one.
1. `Toggle Theme`: If the current theme of the app is `light`, it will change the theme to `dark`, vice versa.

We want to test if these buttons do work as expected under both light and dark theme. With this, we would like to have the following steps for both themes:

1. Check if the simple counter app correctly opens in the specified theme. We have light and dark (default) themes.
1. Press `+` once, assert the count equals to one.
1. Press `-` once, assert the count equals to zero.
1. Press `Toggle Theme` and see if the theme do change.
1. The application do gracefully close.

To do this, we will go through the following steps:

1. Setup: Start the `simple-counter` app in the Mir server.
1. Creating tests with interactive mode: We will experiment different keywords and grab suitable templates - getting the things that we needed to write a test suite.
1. Creating a test suite: Write test scripts and organize things into a directory structure that YARF can understand.
1. Adding a test suite for the light mode: Our `simple-counter` app has a `light` mode! We extend our test suite to cover our tests to the light mode as well.

## Setup

First, we start the Mir server up as described in the [getting started tutorial][getting-started]. Then we install `uv` following the [official installation guide][uv-installation-guide].
After that we run the `simple-counter`:

```{code-block} bash
---
caption: The commands that starts a virtual environment and running the 
  simple-counter app inside it.
---
uv venv --python=/usr/bin/python3 --system-site-packages --project=$(pwd)/examples/yarf-example-simple-counter
uv --project=$(pwd)/examples/yarf-example-simple-counter run simple-counter &
```

After this, we should see our simple counter popped up in the mir server:

```{figure} ./images/mir_test_tools_with_simple_counter_window.png
---
alt: The mir-test-tools window with simple counter running.
---
The `mir-test-tools` window with simple counter running.
```

Now we are ready to write a test suite.

## Creating tests with interactive mode

In this section, We will first utilize the interactive mode in YARF to test different robot commands and grab required templates. Then, we will structure the commands and the templates we got into a proper test suite. Finally, we will run this test suite using YARF with Mir.

Let's start YARF in interactive mode:

```{code-block} bash
---
caption: Command starting YARF interactive mode with Mir platform.
---
$ yarf --platform Mir
```

To work on the five testing steps we discussed earlier, we can identify from the `keywords` command or the [reference page][reference-resource-docs] that some of the useful keywords are:

1. `Match`: Grab screenshots and compare until there's a match with the provided template or timeout. We can use this keyword to check if the simple counter app correctly opens in the specified theme.
1. `Click ${button} Button On ${destination}`: Move the virtual pointer to the destination and click the button. We can use this keyword to left click on a button we want.
1. `Match Text`: Wait for specified text to appear on screen and get the position of the best match. The region can be specified directly in the robot file using `RPA.core.geometry.to_region`. We can use this keyword to check the count is what we expected.
1. `Keys Combo`: Press and release a combination of keys. :param combo: list of keys to press at the same time. We can use this to close the application by pressing `Alt + F4`.

`Match` and `Click ${button} Button On ${destination}` use template matching, so we need to provide templates for these two keywords. In interactive mode, we provided a `Grab Templates` keyword that opens an ROI selector to allow our users to select templates.

```{figure} ./images/roi_selector_selecting_templates.png
---
alt: ROI selector from running the Grab Templates keyword, selecting template 
  toggle_theme.png.
---
ROI selector from running the `Grab Templates` keyword, selecting template `toggle_theme.png`.
```

At the same time, in the console we should expect something like:

```{code-block} bash
---
caption: Console output from running the Grab Templates keyword.
---
>>>>> Enter interactive shell
...
> Interactive.Grab Templates   simple_counter   +   -   toggle_theme
...
Click and drag to select and save an ROI, press Esc to exit the ROI selector.
ROI saved as /path/to/simple_counter.png
ROI saved as /path/to/+.png
ROI saved as /path/to/-.png
ROI saved as /path/to/toggle_theme.png
>
```

We should have the following templates at this point:

```{figure} ./images/dark_theme_templates.png
---
alt: Dark theme templates for the simple counter app.
---
Dark theme templates for the simple counter app.
```

For more information about the keywords, please visit the interactive library reference [here][reference-lib-docs].

Now, let's test our keywords and templates:

```{code-block} bash
---
caption: Testing out different keywords.
---
> Match   template=/path/to/simple_counter.png
...
< [{'left': 316, 'top': 182, 'right': 624, 'bottom': 407, 'path': '/path/to/simple_counter.png'}]
> Click LEFT Button on /path/to/+.png                                                                       # ΔT: 0.141s
INFO:root:Scanned image in 0.10 seconds
> Match Text   text=Count: 1                                                                                # ΔT: 0.084s
< ([{'text': 'Count: 1', 'region': Region(left=416, top=250, right=525, bottom=281), 'confidence': 100.0}], <PIL.Image.Image image mode=RGBA size=1280x1024 at 0x7011F836AE40>)
> Click LEFT Button on /path/to/-.png                                                                       # ΔT: 0.374s
INFO:root:Scanned image in 0.07 seconds
> Match Text   text=Count: 0
< ([{'text': 'Count: 0', 'region': Region(left=415, top=248, right=526, bottom=281), 'confidence': 100.0}], <PIL.Image.Image image mode=RGBA size=1280x1024 at 0x7011F81CB4D0>)
> Click LEFT Button on /path/to/toggle_theme.png                                                            # ΔT: 0.090s
INFO:root:Scanned image in 0.08 seconds
> Hid.Move Pointer To Absolute  x=0  y=0   # This is to move away the pointer from the application.
>                                                                                                           # ΔT: 0.002s
> Interactive.Grab Templates   simple_counter_toggled   # Grab the template for the simple counter in light theme here.
...
Click and drag to select and save an ROI, press Esc to exit the ROI selector.
ROI saved as /path/to/simple_counter_toggled.png
> Match  /path/to/simple_counter_toggled.png
INFO:root:Scanned image in 0.07 seconds
< [{'left': 317, 'top': 177, 'right': 624, 'bottom': 407, 'path': '/path/to/simple_counter_toggled.png'}]
>                                                                                                           # ΔT: 0.077s
> Keys Combo   Alt_L   F4
>                                                                                                           # ΔT: 0.005s
```

```{caution}
Sometimes, the keywords name clashes and Robot Framework cannot identify the correct keyword.
In this case, we need to explicitly specify the library name. For example: `Hid.Move Pointer To Absolute  x=0  y=0`.
```

In the meantime, we should see the simple counter inside the Mir server has the following changes:

```{figure} ./images/changes_of_simple_counter.png
---
alt: Changes of the simple counter app inside Mir server.
---
Changes of the simple counter app inside Mir server.
```

We can see that the keywords and templates gives the expected results.

## Creating a test suite

Now, we can turn the templates we have and the verified keywords to a proper test suite as in `examples/yarf-example-simple-counter/yarf_tests` in this repository:

```{code-block} bash
---
caption: Directory structure for the simple counter test suite.
---
yarf_tests
├── button_tests.robot
├── simple_counter.png
├── simple_counter_toggled.png
└── buttons
    ├── toggle_theme.png
    ├── +.png
    └── -.png
```

In the `yarf_tests` directory, `button_test.robot` is the test script for running the tests and all other `.png`s are the templates we have got from the YARF interactive mode earlier. We will use the templates along with the keywords that we tested earlier to come up with a proper test suite in the `button_test.robot` script.

```{code-block} robotframework
---
caption: button_tests.robot
linenos:
---
*** Settings ***
Resource        kvm.resource


*** Test Cases ***
Assert simple counter started
    Match                   ${CURDIR}/simple_counter.png

Increase the counter and assert count
    Click LEFT Button on ${CURDIR}/buttons/+.png
    Match Text              Count: 1

Decrease the counter and assert count
    Click LEFT Button on ${CURDIR}/buttons/-.png
    Match Text              Count: 0

Toggle theme and assert the theme changed
    Click LEFT Button on ${CURDIR}/buttons/toggle_theme.png
    Hid.Move Pointer To Absolute            x=0                     y=0
    Match                   ${CURDIR}/simple_counter_toggled.png

Close the simple counter
    Keys Combo              Alt_L                   F4

Assert simple counter closed
    Wait Until Keyword Succeeds                     5                       1
    ...                     Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match                   ${CURDIR}/simple_counter_toggled.png                         0

```

In the `button_tests.robot` script above:

1. `kvm.resource` is a resource file that provides our required keywords.
1. `${CURDIR}` is a useful builtin variable to reference the current directory. For more details please visit the the Robot Frame documentation [here][rf-docs-builtin-vars].
1. `Wait Until Keyword Succeeds` and `Run Keyword And Expect Error` are two builtin keywords provided by Robot Framework. For details, please visit their documentation [here][rf-docs-builtin]

For detailed information of how to construct a more advanced test suite please visit our [how-to guide][how-to-guide-index].

Now we have our test suite in place, we can now test our test suite using the YARF command with the Mir server and simple counter app opened:

```{code-block} bash
---
caption: Command for running a test suite.
---
$ yarf --platform=Mir /path/to/yarf_tests
```

We should see some output like below:

```{code-block} bash
---
caption: Output from running the yarf_test test suite.
---
$ yarf --platform=Mir /path/to/yarf_tests
INFO:yarf.rf_libraries.suite_parser:Selected assets:
  button_tests.robot
  simple_counter_toggled.png
  simple_counter.png
  buttons/+.png
  buttons/toggle_theme.png
  buttons/-.png
==============================================================================
yarf_tests
==============================================================================
INFO:RPA.core.certificates:Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)
2025-07-31 08:29:41,669 - RPA.core.certificates - INFO - Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)
yarf_tests.Button Tests
==============================================================================
Assert simple counter started                                         INFO:root:Scanned image in 0.08 seconds
Assert simple counter started                                         | PASS |
------------------------------------------------------------------------------
Increase the counter and assert count                                 INFO:root:Scanned image in 0.06 seconds
Increase the counter and assert count                                 | PASS |
------------------------------------------------------------------------------
Decrease the counter and assert count                                 INFO:root:Scanned image in 0.06 seconds
Decrease the counter and assert count                                 | PASS |
------------------------------------------------------------------------------
Toggle theme and assert the theme changed                             INFO:root:Scanned image in 0.06 seconds
.INFO:root:Scanned image in 0.07 seconds
Toggle theme and assert the theme changed                             | PASS |
------------------------------------------------------------------------------
Close the simple counter                                              | PASS |
------------------------------------------------------------------------------
Assert simple counter closed                                          | PASS |
------------------------------------------------------------------------------
yarf_tests.Button Tests                                               | PASS |
6 tests, 6 passed, 0 failed
==============================================================================
yarf_tests                                                            | PASS |
6 tests, 6 passed, 0 failed
==============================================================================
Output:  /path/to/yarf-outdir/output.xml
Log:     /path/to/yarf-outdir/log.html
Report:  /path/to/yarf-outdir/report.html
INFO:yarf.main:Results exported to: /path/to/yarf-outdir
```

We can see that the test suite runs successfully!

```{tip}
In case of errors/failures occurred, the results exported to `/path/to/yarf-outdir` is a good place to understand what has gone wrong.
```

## Adding a test suite for the light mode

With our dark theme tests in place, we still need to test our simple counter app in light theme variant. In YARF, we support testing variants with a `--variant` option in the `yarf` command. With this, we can use the same test suite with different templates.

Before running the test suite for the light theme, we need to take the light theme templates so that our keywords can properly find the buttons in the specified theme. We can use the `Grab Template` keyword provided in the interactive mode for this again.

```{code-block} bash
---
caption: Starting the simple counter in light theme and grab templates using the
  interactive mode.
---
uv --project=$(pwd)/examples/yarf-example-simple-counter run simple-counter --theme=light &
$ yarf --platform Mir
...
>>>>> Enter interactive shell
iRobot can interpret single or multiple keyword calls,
as well as FOR, IF, WHILE, TRY
and resource file syntax like *** Keywords*** or *** Variables ***.

Type "help" for more information.
> Interactive.Grab Templates   simple_counter   +   -   toggle_theme
...
Click and drag to select and save an ROI, press Esc to exit the ROI selector.
ROI saved as /path/to/simple_counter.png
ROI saved as /path/to/+.png
ROI saved as /path/to/-.png
ROI saved as /path/to/toggle_theme.png
>
> Interactive.Grab Templates   simple_counter_toggled
...
Click and drag to select and save an ROI, press Esc to exit the ROI selector.
ROI saved as /path/to/simple_counter_toggled.png
>
```

Please also test the grabbed templates with appropriate keywords to verify that the templates are working.

At the end, we should have the following templates for the light and dark theme respectively:

```{figure} ./images/light_and_dark_theme_templates.png
---
alt: Light and dark theme templates.
---
Light and dark theme templates.
```

Now, we need to create a `variants` directory under the `yarf_tests` directory since YARF will look into this directory for variants.
With this, we can put all the light theme templates under the `variants/light` directory as below:

```{code-block} bash
---
caption: Directory structure for the simple counter test suite with light 
  variant.
---
yarf_tests
├── button_tests.robot
├── simple_counter.png
├── simple_counter_toggled.png
├── buttons
|   ├── toggle_theme.png
|   ├── +.png
|   └── -.png
└── variants
    └── light
        ├── simple_counter.png
        ├── simple_counter_toggled.png
        └── buttons
            ├── toggle_theme.png
            ├── +.png
            └── -.png
```

```{note}
The templates names in the variant should be the same as the default ones under the top level directory (`yarf_tests` in this case).
```

We can now test our test suite with the light variant with the command:

```{code-block} bash
---
caption: YARF command for running the test suite with the light theme variant.
---
$ yarf --platform=Mir --variant=light /path/to/yarf_tests
```

We should see an output similar to the following, notice how the asset path changed when YARF collects the templates:

```{code-block} bash
---
caption: Output from running the yarf_test test suite on the light theme 
  variant.
emphasize-lines: 2-8
---
$ yarf --platform=Mir --variant=light /path/to/yarf_tests
INFO:yarf.rf_libraries.suite_parser:Selected assets:
  button_tests.robot
  variants/light/simple_counter_toggled.png
  variants/light/simple_counter.png
  variants/light/buttons/+.png
  variants/light/buttons/toggle_theme.png
  variants/light/buttons/-.png
==============================================================================
yarf_tests
==============================================================================
INFO:RPA.core.certificates:Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)
2025-07-31 08:33:43,696 - RPA.core.certificates - INFO - Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)
yarf_tests.Button Tests
==============================================================================
Assert simple counter started                                         INFO:root:Scanned image in 0.09 seconds
Assert simple counter started                                         | PASS |
------------------------------------------------------------------------------
Increase the counter and assert count                                 INFO:root:Scanned image in 0.07 seconds
Increase the counter and assert count                                 | PASS |
------------------------------------------------------------------------------
Decrease the counter and assert count                                 INFO:root:Scanned image in 0.09 seconds
Decrease the counter and assert count                                 | PASS |
------------------------------------------------------------------------------
Toggle theme and assert the theme changed                             INFO:root:Scanned image in 0.09 seconds
.INFO:root:Scanned image in 0.07 seconds
Toggle theme and assert the theme changed                             | PASS |
------------------------------------------------------------------------------
Close the simple counter                                              | PASS |
------------------------------------------------------------------------------
Assert simple counter closed                                          | PASS |
------------------------------------------------------------------------------
yarf_tests.Button Tests                                               | PASS |
6 tests, 6 passed, 0 failed
==============================================================================
yarf_tests                                                            | PASS |
6 tests, 6 passed, 0 failed
==============================================================================
Output:  /path/to/yarf-outdir/output.xml
Log:     /path/to/yarf-outdir/log.html
Report:  /path/to/yarf-outdir/report.html
INFO:yarf.main:Results exported to: /path/to/yarf-outdir
```

Now we have our test suite works for the light theme as well!

We have now successfully built a test suite to test the `+`, `-`, `Toggle Theme` buttons that we (pretended to have) developed in both dark and light theme of the simple counter app.

```{tip}
YARF can be used in CI pipelines to validate your GUI application on multiple platforms. As an example, Mir could be used on Pull Requests given how fast it is to boostrap, while Vnc can be used on tag targeting multiple virtual machines or even remote hardware (if you self host your runner).
```

[getting-started]: getting_started.md
[how-to-guide-index]: ../how-to/index.md
[reference-lib-docs]: ../reference/rf_libraries-libraries.md
[rf-docs-builtin]: https://robotframework.org/robotframework/latest/libraries/BuiltIn.html
[rf-docs-builtin-vars]: https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#built-in-variables
[uv-installation-guide]: https://docs.astral.sh/uv/getting-started/installation/
