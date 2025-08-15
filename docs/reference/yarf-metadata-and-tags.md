<!-- vale off -->

# YARF metadata and tags

<!-- vale on -->

In yarf we support the following metadata and tags in addition to the [official ones](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#tagging-test-cases).

## Metadata

We can add metadata in the `*** Settings ***` section in `__init__.robot` of a suite so that we can apply the metadata for all tasks in the test suite.

### Display resolutions

This metadata specifies the display resolutions of different displays in the form of `yarf:displays     <screen_1_name>:W1xH1 <screen_2_name>:W2xH2 ... <screen_n_name>:WnxHn`, where `<screen_x_name>` is optional. For example:

```{code-block} text
*** Settings ***
Metadata       yarf:displays       HDMI_1:1920x1080 Camera_1:1280x1080 800x600
```

<u><center>Code Snippet: An example of a `__init__.robot` file using `yarf:displays` metadata under the `Settings` section</center></u>

## Tags

<!-- vale off -->

### YARF version

<!-- vale on -->

We can add this tag in the `Test Tags` section under `*** Settings ***` or under individual tasks. For example:

```{code-block} text
*** Settings ***
Documentation       Example
Test Tags           robot:stop-on-failure   yarf:version: >= 1.0.0
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    Print Library

Task 2
    [Tags]            yarf:version: >= 2.0.0
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using the tag `yarf:version: <operator> X.Y`</center></u>

```{Note}
For this tag, spacing is important.
`robot:stop-on-failure` is a [reserved tag](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#reserved-tags).
```

Depends on the version of YARF that we are using, different task(s) will run:

| YARF Version `x`    | Tasks that will run |
| ------------------- | ------------------- |
| `x` < 1.0.0         | None                |
| 1.0.0 ≤ `x` ≤ 2.0.0 | `Task 1`            |
| `x` > 2.0.0         | `Task 1`, `Task 2`  |

We support the following operators:

1. `<`
1. `>`
1. `<=`
1. `>=`
1. `==`
1. `!=`

With this tag, we can control which task will run in the suite with respect to YARF version.

<!-- vale off -->

### Category ID

<!-- vale on -->

This tag specifies the category of a test case in the form of `yarf:category_id: <category_namespace>::<category>`. We can add this tag in the `Test Tags` section under `*** Settings ***` so that we can apply the tag for all tasks under the file, or we can add the tag under individual tasks. For example:

```{code-block} text
*** Settings ***
Documentation       Example
Test Tags           yarf:category_id: com.canonical.category::Category-A
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    Print Library

Task 2
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using the tag `yarf:category_id: full_id` under the `Settings` section</center></u>

```{code-block} text
*** Settings ***
Documentation       Example
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    [Tags]            yarf:category_id: com.canonical.category::Category-B
    Print Library

Task 2
    [Tags]            yarf:category_id: com.canonical.category::Category-C
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using the tag `yarf:category_id: full_id` under individual tasks</center></u>

### Certification status

This tag specifies the certification status of a test case in the form of `yarf:certification_status: <value>`, where `<value>` can either be `blocker` or `non-blocker`. We can add this tag under each test case. For example:

```{code-block} text
*** Settings ***
Documentation       Example
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    [Tags]            yarf:certification_status: blocker
    Print Library

Task 2
    [Tags]            yarf:certification_status: non-blocker
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using the tag `yarf:certification_status: <value>` under individual tasks</center></u>

<!-- vale off -->

### Test group ID

<!-- vale on -->

This tag specifies the scenario group of a test case in the form of `yarf:test_group_id: <test_group_namespace>::<group>`. We can add this tag in the `Test Tags` section under `*** Settings ***` so that we can apply the tag for all tasks under the file, or we can add the tag under individual tasks. For example:

```{code-block} text
*** Settings ***
Documentation       Example
Test Tags           yarf:test_group_id: com.canonical.test-group::provisioning
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1 for Provisioning
    Print Library

Task 2 for Provisioning
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using the tag `yarf:test_group_id: <test_group_namespace>::<group>` under the `Settings` section</center></u>

```{code-block} text
*** Settings ***
Documentation       Example
Library             some_lib.py
Resource            smoke.resource

*** Tasks ***
Task 1
    [Tags]            yarf:test_group_id: com.canonical.test-group::scenario_A
    Print Library

Task 2
    [Tags]            yarf:test_group_id: com.canonical.test-group::scenario_B
    Log To Console    message 1
```

<u><center>Code Snippet: An example of a test robot file using the tag `yarf:test_group_id: <test_group_namespace>::<group>` under individual tasks</center></u>

### Exit on failure

We can add this tag `robot:exit-on-failure` in the `Test Tags` section under `*** Settings ***`. With this, YARF will exit immediately on failure when it hits a failure in a task. For example:

```{code-block} text
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

<u><center>Code Snippet: An example of a test robot file using the tag `robot:exit-on-failure` under the `Settings` section</center></u>

### Exit on error

We can add this tag `robot:exit-on-error` in the `Test Tags` section under `*** Settings ***`. With this, YARF will exit immediately on failure when it hits an error in a task. For example:

```{code-block} text
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

<u><center>Code Snippet: An example of a test robot file using the tag `robot:exit-on-error` under the `Settings` section</center></u>
