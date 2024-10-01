# Write a Robot File with YARF Tags

This guide will show how to write a robot file with yarf tags.
For details of how to write a general test data robot file please visit the [Robot Framework official documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-data-sections)

## YARF Tags

In yarf we will support the following tags in addition to the [official ones](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#tagging-test-cases):

1. [YARF minimum version](#yarf-minimum-version): `yarf:min-version-X.Y.Z`, where `X`, `Y` and `Z` are digits and `X.Y.Z` combined together representing the minimum YARF version number required for the test suite.
1. [Exit on failure](#exit-on-failure): `robot:exit-on-failure`, YARF will exit immediately on failure.
1. [Exit on error](#exit-on-error): `robot:exit-on-error`, YARF will exit immediately on error.

### YARF minimum version

We can add this tag in the `Test Tags` section under `*** Settings ***` or under individual tasks. For example:

```text
*** Settings ***
Documentation       Example
Test Tags           robot:stop-on-failure   yarf:min-version-1.0.0
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    Print Library

Task 2
    [Tags]            yarf:min-version-2.0.0
    Log To Console    message 1
```

<u><center>Code Snippet 1: An example of a test data robot file using the tag `yarf:min-version-X.Y`</center></u>

```{Note}
`robot:stop-on-failure` is a [reserved tag](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#reserved-tags)
```

Depends on the version of YARF that we are using, different task(s) will run:

| YARF Version `x`    | Tasks that will run |
| ------------------- | ------------------- |
| `x` \< 1.0.0        | None                |
| 1.0.0 ≤ `x` ≤ 2.0.0 | `Task 1`            |
| `x` > 2.0.0         | `Task 1`, `Task 2`  |

With this tag, we can control which task will run in the suite.

### Exit on failure

We can add this tag `robot:exit-on-failure` in the `Test Tags` section under `*** Settings ***`. For example:

```text
*** Settings ***
Documentation       Example
Test Tags           robot:exit-on-failure
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    Fail

Task 2
    Log To Console    This will not be executed.
```

With this, YARF will exit immediately on failure when it hits a failure in a task.

### Exit on error

We can add this tag `robot:exit-on-error` in the `Test Tags` section under `*** Settings ***`. For example:

```text
*** Settings ***
Documentation       Example
Test Tags           robot:exit-on-error
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    Fatal Error

Task 2
    Log To Console    This will not be executed.
```

With this, YARF will exit immediately on failure when it hits an error in a task.
