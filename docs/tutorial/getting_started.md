# Getting started

**YARF** is a tool built upon [Robot Framework][robot-framework] that allows developers to build complex visual test scenarios and bootstrap them locally, and then work towards automated runs in continuous integration (CI) and use of platforms/fixtures with minimal effort. In YARF, we support the Mir as one of our default platform.

**Mir** is a display server that is suitable for local development and continuous integration. In this tutorial, we will use Mir to display the calcualtor and then use YARF to perform actions and run tests on it. For details please visit [here][mir-docs].

In this tutorial, we will go through the process of setting up YARF and a Mir server, then we will start a calculator app inside the Mir server and use YARF to do some simple calculations.

This tutorial is divided into the following sections:

1. Setup
1. Exploring YARF

## Setup

<!-- vale off -->

### Installing YARF and dependencies

<!-- vale on -->

First of all, we will install YARF, we can simply run:

```{code-block} bash
---
caption: The command to install the YARF snap.
---
sudo snap install yarf
```

Optionally connect the following snap interface to allow our optical character recognition (OCR) algorithm to speed up the process:

```{code-block} bash
---
caption: The command to connect YARF's process-control interface.
---
snap connect yarf:process-control
```

Next, we need to install [`mir-test-tools`][mir-tests-tools], a snap that provides an HID enabled demo Mir server - In this server, we can control the mouse and keyboard.

```{code-block} bash
---
caption: The command to install mir-test-tools
---
sudo snap install mir-test-tools
```

### Starting the Mir server

Now, let's start the Mir server:

```{code-block} bash
---
caption: The command to start the mir-test-tools demo server with virtual 
  pointer.
---
export WAYLAND_DISPLAY=wayland-0

mir-test-tools.demo-server \
    --add-wayland-extensions zwlr_screencopy_manager_v1:zwlr_virtual_pointer_manager_v1 &
```

```{note}
`WAYLAND_DISPLAY` is a variable that is only used inside the Mir virtual server, not the running desktop.
```

We should see some output like:

```{code-block} bash
---
caption: Output of starting mir-test-tools.demo-server.
---
$ mir-test-tools.demo-server \
    --add-wayland-extensions zwlr_screencopy_manager_v1:zwlr_virtual_pointer_manager_v1 &
[1] 4160206

[2025-07-30 15:51:06.763863] <information> mirserver: Starting
...
[2025-07-30 15:51:08.360008] <information> mirserver: Initial display configuration:
[2025-07-30 15:51:08.360031] <information> mirserver: * Output 1: unknown connected, used
[2025-07-30 15:51:08.360039] <information> mirserver: . |_ Physical size 9.7" 193x155mm
[2025-07-30 15:51:08.360042] <information> mirserver: . |_ Power is on
[2025-07-30 15:51:08.360047] <information> mirserver: . |_ Current mode 1280x1024 120.00Hz
[2025-07-30 15:51:08.360050] <information> mirserver: . |_ Preferred mode 1280x1024 120.00Hz
[2025-07-30 15:51:08.360054] <information> mirserver: . |_ Orientation normal
[2025-07-30 15:51:08.360059] <information> mirserver: . |_ Logical size 1280x1024
[2025-07-30 15:51:08.360062] <information> mirserver: . |_ Logical position +0+0
[2025-07-30 15:51:08.360065] <information> mirserver: . |_ Scaling factor: 1.00
```

And a black window with a pointer should pop up:

```{figure} ./images/mir_test_tools_window.png
---
alt: The mir test tools window
width: 50%
---
The mir test tools window
```

### Starting the calculator app

Now, we can start our calculator by running under the same terminal:

```{code-block} bash
---
caption: The commands that starts a calculator.
---
gnome-calculator &
```

Then we should see our simple counter popped up in the mir server:

```{figure} ./images/mir_test_tools_with_calculator_window.png
---
alt: The mir-test-tools window with the calculator running.
---
The `mir-test-tools` window with the calculator running.
```

<!-- vale off -->

## Exploring YARF

<!-- vale on -->

After setup, we can start exploring YARF. In YARF we can control the pointer and keyboard using different functions called `keywords`, and we provided an interactive mode for users to test out different commands.

### Entering the interactive mode

To get into interactive mode, we can run:

```{code-block} bash
---
caption: YARF interactive mode with Mir platform.
---
$ yarf --platform Mir
INFO:RPA.core.certificates:Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)
2025-07-30 17:28:11,998 - RPA.core.certificates - INFO - Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)


INFO: *** Welcome to the YARF interactive console. ***
INFO: You can use this console to execute Robot Framework keywords interactively.
INFO: The value of ${CURDIR} is CWD, you can change it using the `Set Variable` keyword.
INFO: You can press RIGHT_ARROW to auto-complete the keyword.
INFO: You can press CRTL + SPACE to view supported keywords on a prefix.
>>>>> Enter interactive shell
iRobot can interpret single or multiple keyword calls,
as well as FOR, IF, WHILE, TRY
and resource file syntax like *** Keywords*** or *** Variables ***.

Type "help" for more information.
>
```

Here, we can run `keywords` to see a list of commands that we can use:

```{code-block} bash
---
caption: YARF interactive mode keywords output.
---
...
>>>>> Enter interactive shell
iRobot can interpret single or multiple keyword calls,
as well as FOR, IF, WHILE, TRY
and resource file syntax like *** Keywords*** or *** Variables ***.

Type "help" for more information.
> keywords
...
< Keywords of library kvm
   Click ${button} Button	 Click a button on the virtual pointer.
   Click ${button} Button On ${destination}	 Move the virtual pointer to the destination and click the button.
   Displace ${point} By (${x}, ${y})	 Shift a point by the specified displacements along the x and y axes.
   Get Center Of ${region}	 Get the center point of a region.
   Move Pointer To ${destination}	 Move the pointer to an absolute position or image template.
   Move Pointer To ${destination} In ${domain}	 Move the pointer to an absolute position or image template.
   Move Pointer To (${x}, ${y})	 Move the pointer to an absolute position.
   Move Pointer To Proportional (${x}, ${y})	 Move the pointer to a destination position given as proportions to the size of the display output.
   Press ${button} Button	 Press a button on the virtual pointer.
   Press And Wait For Match
   Press Combo And Match	 If the provided template is not already matching, press a key combination until it does.
   Press Key And Match	 If the provided template is not already matching, press a key until it does.
   Release ${button} Button	 Release a button on the virtual pointer.
   Release Buttons	 Release all buttons on the virtual pointer.
   Walk Pointer To ${destination}	 Moves the pointer in incremental steps from the current pointer position to an absolute position or image template.
   Walk Pointer To (${x}, ${y})	 Move the pointer in incremental steps from the current pointer position to an absolute position.
   Walk Pointer To Proportional (${x}, ${y})	 Move the pointer in incremental steps from the current pointer position to a destination position given as proportions to the size of the display output.
```

In YARF, we supports the Robot Framework built-in keywords and we also developed a list of keywords for more convenient use cases.
For a more detailed list of keywords developed under YARF, please visit the [reference page][reference-resource-docs].

### Start using keywords

Now let's use the YARF interactive mode to do some simple maths. With the cursor blinking in the calculator. Use the following command in the interactive console:

```{code-block} bash
---
caption: Using the command `Type String`.
---
> Type String   7*6=
> 
```

This command will type `7*6=` in the calculator and should give a result equals to `42`.

```{figure} ./images/calculator_with_simple_formula.png
---
alt: The calculator calculating a simple formula.
---
The calculator calculating a simple formula.
```

Alternatively, instead of simulating keyboard input, we can also instruct YARF to simulate mouse clicks on the graphic interface using the `Click ${button} Button On ${destination}` keyword. To do this, we need to tell the keyword which UI element to target by providing a template.

In the interactive mode, we provided a `Grab Templates` keyword that opens an ROI (Region of Interest) selector to allow our users to select templates.

```{code-block} bash
---
caption: Console output from running the Grab Templates keyword on the 
  calculator.
---
>>>>> Enter interactive shell
...
Interactive.Grab Templates   7   *   6   =                                                         # ΔT: 7.686s
Click and drag to select and save an ROI, press Esc to exit the ROI selector.
ROI saved as /path/to/7.png
ROI saved as /path/to/*.png
ROI saved as /path/to/6.png
ROI saved as /path/to/=.png
>
```

```{figure} ./images/roi_selector_selecting_calculator_7.png
---
alt: The ROI selector selecting the 7 button in the calculator.
---
The ROI selector selecting the 7 button in the calculator.
```

Just follow the instructions in the ROI selector to capture the following templates:

```{figure} ./images/calculator_templates.png
---
alt: The templates required for calculating 7*6=42.
width: 50%
---
The templates required for calculating 7*6=42.
```

Now with the templates in place we can use the function `Click ${button} Button On ${destination}` to click the buttons:

```{code-block} bash
---
caption: Console output from running the Grab Templates keyword on the 
  calculator.
---
>>>>> Enter interactive shell
...
> Click LEFT Button On /path/to/7.png                                                              # ΔT: 0.114s
INFO:root:Scanned image in 0.12 seconds
> Click LEFT Button On *.png                                                                       # ΔT: 0.138s
INFO:root:Scanned image in 0.09 seconds
> Click LEFT Button On 6.png                                                                       # ΔT: 0.107s
INFO:root:Scanned image in 0.09 seconds
> Click LEFT Button On =.png                                                                       # ΔT: 0.105s
INFO:root:Scanned image in 0.11 seconds
> 
```

Then we should see the pointer inside the mir server moving across the buttons on the calculator and give the answer `42` as the same before.

In this tutorial, we have successfully setup the mir server and use YARF to control the keyboard and pointer to do simple calculations on the calculator app. Feel free to try out other keywords!

[mir-docs]: https://canonical-mir.readthedocs-hosted.com/stable/
[mir-tests-tools]: https://snapcraft.io/mir-test-tools
[reference-resource-docs]: ../reference/rf_libraries-resources.md
[robot-framework]: https://robotframework.org/
