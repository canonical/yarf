# Write a Robot File with YARF Tags

This guide will show how to write a robot file with yarf tags.
For details of how to write a general test robot file please visit the [Robot Framework official documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-sections)

## Adding a YARF tag to a robot file

There are two ways to add a YARF tag to a robot file:

1. Add the tag to the `Settings` section of the robot file, in this case, the tag will be applied to each of the tasks under the robot file. For example:

```{code-block} text
*** Settings ***
Documentation       Example
Test Tags           yarf:yarf_tagA: valueA
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    Print Library

Task 2
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using a YARF tag under the Settings section</center></u>

1. Add the tag to individual tasks in the robot file, in this case the tag will be applied to the corresponding tasks only. For example:

```{code-block} text
*** Settings ***
Documentation       Example
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    [Tags]            yarf:yarf_tagB: >= valueB
    Print Library

Task 2
    [Tags]            yarf:yarf_tagC: valueC
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using the tag `yarf:version: <operator> X.Y`</center></u>

For details of the tags we supported in YARF, please visit [here](../reference/yarf-tags.md).
