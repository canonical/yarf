# Write a robot file with YARF tags

This guide will show how to write a robot file with yarf metadata and tags.
For details of how to write a general test robot file please visit the [Robot Framework official documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-sections)

For details of the metadata and tags we supported in YARF, please visit [here](../reference/yarf-metadata-and-tags.md).

## Adding YARF metadata to a robot suite

To add YARF metadata to a robot suite, we will create a `__init__.robot` file under the suite directory:

```{code-block} bash
suite
├── __init__.robot
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

<u><center>Code Snippet: An example of a test suite file structure with an `__init__.robot` file</center></u>

In the `__init__.robot` file, we will then specify the metadata under the `*** Settings ***` section. For example:

```{code-block} text
*** Settings ***
Metadata       metadata_nameA       metadata_valueA
```

<u><center>Code Snippet: An example of an `__init__.robot` file with a Metadata specified</center></u>

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
