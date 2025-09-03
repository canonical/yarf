*** Settings ***
Resource        kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::plugin
...    yarf:test_group_id: com.canonical.yarf::integration


*** Test Cases ***
Verify Video Input Keywords
    ${result}=              PlatformVideoInput.Start Video Input
    Should Be Equal         ${result}               STARTED

    ${result}=              PlatformVideoInput.Grab Screenshot
    Should Be Equal         ${result}               SCREENSHOT

    ${result}=              PlatformVideoInput.Stop Video Input
    Should Be Equal         ${result}               STOPPED

Verify HID Keywords
    ${result}=              PlatformHid.Type String                         Hello, World!
    Should Be Equal         ${result}               Hello, World!

    ${result}=              PlatformHid.Click Pointer Button                left
    Should Be Equal         ${result}               left

    ${result}=              PlatformHid.Press Pointer Button                right
    Should Be Equal         ${result}               right

    ${result}=              PlatformHid.Release Pointer Button              middle
    Should Be Equal         ${result}               middle
