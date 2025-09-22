*** Settings ***
Resource        kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::plugin
...    yarf:test_group_id: com.canonical.yarf::integration


*** Test Cases ***
Verify Video Input Keywords
    ${result}=              Start Video Input
    Should Be Equal         ${result}               STARTED

    ${result}=              Grab Screenshot
    Should Be Equal         ${result}               SCREENSHOT

    ${result}=              Stop Video Input
    Should Be Equal         ${result}               STOPPED

Verify HID Keywords
    ${result}=              Type String             Hello, World!
    Should Be Equal         ${result}               Hello, World!

    ${result}=              Hid.Click Pointer Button                        left
    Should Be Equal         ${result}               left

    ${result}=              Hid.Press Pointer Button                        right
    Should Be Equal         ${result}               right

    ${result}=              Hid.Release Pointer Button                      middle
    Should Be Equal         ${result}               middle
