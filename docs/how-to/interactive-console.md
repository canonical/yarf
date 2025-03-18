# Interactive console

The interactive mode will help you interact with platform of choice without providing a test suite, running your test keyword by keyword. After closing the shell, the user will be able to write their own Test Suite with the help of the command history.

In this document, we will walk through how to use the interactive console in YARF:

1. [Entering the interactive console](#entering-the-interactive-console)
1. [Exploring the interactive console](#exploring-in-the-interactive-console)

## Entering the interactive console

We can enter the interactive console by supplying an empty suite path. For example, in terms of Example, we can use:

```{code-block} bash
Example_IP=<ip> yarf
```

<u><center>Code Snippet: Example's `yarf` command that enters interactive console</center></u>

After we enter the command, we should see something similar to the following:

```{code-block} bash
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

<u><center>Code Snippet: `yarf`'s interactive console</center></u>

With this, we can start using the interactive console.

## Exploring in the interactive console

In the interactive console, we can see information about the built-in and YARF specific libraries along with their corresponding keywords by using the commands `libs` and `keywords` respectively:

```{code-block} text
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
       This class provides access to Example video input devices.
   Hid
       This class provides the Robot interface for HID interactions.
   HID
       This class provides the Robot interface for HID interactions.
   VIDEO
       This class provides access to Example video input devices.
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
   Move Pointer To ${destination}        Move the pointer to an absolute position or image template.
   Move Pointer To (${x}, ${y})  Move the pointer to an absolute position.
   Move Pointer To Proportional (${x}, ${y})     Move the pointer to a destination position given as proportions to the size of the display output.
   ...
>
```

<u><center>Code Snippet: Truncated result of using the commands `libs` and `keywords` respectively</center></u>

We can then study the information given and try out the supported keywords. For example:

```{code-block} text
> Walk Pointer To foo.png
INFO:root:Scanned image in 0.07 seconds
< (595, 568)
> Walk Pointer To (0, 0)                                            # ΔT: 0.097s
> Walk Pointer To foo.png                                           # ΔT: 0.546s
INFO:root:Scanned image in 0.06 seconds
```

<u><center>Snippet: An example of using a keyword `Walk Pointer To`</center></u>

We can use the interactive console as if we are scripting a `.robot` file. For more information about the supported commands, please use the `help` command inside the interactive console.

When we exit the interactive console, YARF will save the console log will be saved in the file `/tmp/yarf-outdir` directory. However, the user can also change it by providing a path to the `--outdir` option in the `yarf` command.

Please note that the interactive console log is just a track record of the commands used by the user in the interactive console session along with timestamps. The user is still responsible to come up with a proper test suite along with the `.robot` scripts required. For more information about how to write a `.robot` script please visit the official [Robot Framework Documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-sections)
