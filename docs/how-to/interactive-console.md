# Interactive console

The interactive mode will help you interact with platform of choice without providing a test suite, running your test keyword by keyword. After closing the shell, the user will be able to write their own Test Suite with the help of the command history.

In this document, we will walk through how to use the interactive console in YARF:

1. [Entering the interactive console](#entering-the-interactive-console)
1. [Exploring the interactive console](#exploring-in-the-interactive-console)

## Entering the interactive console

We can enter the interactive console by supplying the platform choice with an empty suite path. For example, in terms of Vnc, we can use:

```{code-block} bash
---
caption: `yarf` command for Vnc that enters interactive console
---
yarf --platform Vnc
```

After we enter the command, we should see something similar to the following:

```{code-block} bash
---
caption: `yarf`'s interactive console
---
WARNING:yarf.main:Removing existing output directory: /tmp/yarf-outdir
INFO:The value of CURDIR is: /path/to/current/directory
INFO:You can change the value of CURDIR by using ${CURDIR}= <path-you-want>

INFO:RPA.core.certificates:Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)
2024-09-11 20:30:26,292 - RPA.core.certificates - INFO - Truststore not in use, HTTPS traffic validated against `certifi` package. (requires Python 3.10.12 and 'pip' 23.2.1 at minimum)
>>>>> Enter interactive shell
iRobot can interpret single or multiple keyword calls,
as well as FOR, IF, WHILE, TRY
and resource file syntax like *** Keywords*** or *** Variables ***.

Type "help" for more information.
>
```

With this, we can start using the interactive console.

## Exploring in the interactive console

In the interactive console, we can see information about the built-in and YARF specific libraries along with their corresponding keywords by using the commands `libs` and `keywords` respectively:

```{code-block} text
---
caption: Truncated result of using the commands `libs` and `keywords` 
  respectively
---
> libs
< Imported libraries:
   BuiltIn 6.1.1
       An always available standard library with often needed keywords.
   Easter
   String 6.1.1
       A library for string manipulation and verification.
   RobotDebug 4.5.0
       Debug Library for RobotFramework.
   Smoke
   VideoInput
       This class provides access to Vnc video input devices.
   Hid
       This class provides the Robot interface for HID interactions.
   HID
       This class provides the Robot interface for HID interactions.
   VIDEO
       This class provides access to Vnc video input devices.
>
> keywords
< Keywords of library BuiltIn
   Call Method   Calls the named method of the given object with the provided arguments.
   Catenate      Catenates the given items together and returns the resulted string.
   ...
< Keywords of library HID
   Click Pointer Button  Press and release the specified pointer button.
   Keys Combo    Press and release a combination of keys. :param combo: list of keys to press at the same time.
   Move Pointer To Absolute      Move the virtual pointer to an absolute position within the output.
   Move Pointer To Proportional  Move the virtual pointer to a position proportional to the size of the output.
   ...
< Keywords of library RobotDebug
   ...
< Keywords of library Smoke
   Print Smoke
< Keywords of library String
   Convert To Lower Case         Converts string to lower case.
   Convert To Title Case         Converts string to title case.
   ...
< Keywords of library VIDEO
   Init  Handles platform-specific initialization.
   Match         Grab screenshots and compare until there's a match with the provided template or timeout.
   Match All     Grab screenshots and compare with the provided templates until a frame is found which matches all templates simultaneously or timeout.
   ...
< Keywords of library kvm
   Click ${button} Button        Click a button on the virtual pointer.
   Displace ${point} By (${x}, ${y})     Shift a point by the specified displacements along the x and y axes.
   Get Center Of ${region}       Get the center point of a region.
   Move Pointer To ${destination}        Move the pointer to an absolute position, image template, or text.
   Move Pointer To ${destination} In ${domain}        Move the pointer to an absolute position, image template, or text, within a given template or region.
   Move Pointer To (${x}, ${y})  Move the pointer to an absolute position.
   Move Pointer To Proportional (${x}, ${y})     Move the pointer to a destination position given as proportions to the size of the display output.
   ...
>
```

We can then study the information given and try out the supported keywords. For example:

```{code-block} text
---
caption: An example of using a keyword `Walk Pointer To`
---
> Walk Pointer To foo.png
INFO:root:Scanned image in 0.07 seconds
< (595, 568)
> Walk Pointer To (0, 0)                                            # ΔT: 0.097s
> Walk Pointer To foo.png                                           # ΔT: 0.546s
INFO:root:Scanned image in 0.06 seconds
```

The `Import Library` or `Import Resource` keywords can be used to reload a library or a resource. For example:

```{code-block} text
---
caption: An example of using keywords `Import Library` and `Import Resource` to 
  reload a library and a resource
---
Import Library     String
Import Resource    /path/to/kvm.resource
```

The interactive console supports the same set of commands as any regular `.robot` file. For more information about the supported commands, please use the `help` command inside the interactive console.

When we exit the interactive console, YARF will save the console log will be saved in the file `/tmp/yarf-outdir` directory. However, the user can also change it by providing a path to the `--outdir` option in the `yarf` command.

Please note that the interactive console log is just a track record of the commands used by the user in the interactive console session along with timestamps. The user is still responsible to come up with a proper test suite along with the `.robot` scripts required. For more information about how to write a `.robot` script please visit the official [Robot Framework Documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-sections)

## Common shortcuts

- `CRTL + SPACE`: Open the auto completion panel.
- `RIGHT_ARROW`: Accept the suggestion.
- `Fn + F5`: Always open the auto completion panel.

## Interactive keywords

There are also interactive mode exclusive Robot Framework keywords that can help us to build test cases. One keyword is `Grab Template` which shows a current screenshot in the platform and allow users to crop templates from it. For the details, please visit the [interactive library](../reference/rf_libraries/interactive_console-Interactive.md)

```{code-block} text
> Interactive.Grab Template
Click and drag to select and save an ROI, press Esc to exit the ROI selector.
ROI saved as /tmp/yarf-outdir/roi_20250415_100750.png
ROI saved as /tmp/yarf-outdir/roi_20250415_100751.png
ROI saved as /tmp/yarf-outdir/roi_20250415_100752.png
>
```
