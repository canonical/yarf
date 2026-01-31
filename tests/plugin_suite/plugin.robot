*** Settings ***
Documentation    Test suite to verify Video Input and HID plugin keywords.
Resource         kvm.resource

Test Tags
...    robot:stop-on-failure
...    yarf:category_id:com.canonical.yarf::plugin
...    yarf:test_group_id:com.canonical.yarf::integration


*** Test Cases ***
Verify Video Input Keywords
    [Documentation]    Test video input start, screenshot, and stop functionality.
    ${result}=    Start Video Input
    Should Be Equal    ${result}    STARTED

    ${result}=    Grab Screenshot
    Should Be Equal    ${result}    SCREENSHOT

    ${result}=    Stop Video Input
    Should Be Equal    ${result}    STOPPED

Verify Hid Keywords
    [Documentation]    Test HID keyboard and pointer button functionality.
    ${result}=    Type String    Hello, World!
    Should Be Equal    ${result}    Hello, World!

    ${result}=    Hid.Click Pointer Button    left
    Should Be Equal    ${result}    left

    ${result}=    Hid.Press Pointer Button    right
    Should Be Equal    ${result}    right

    ${result}=    Hid.Release Pointer Button    middle
    Should Be Equal    ${result}    middle
