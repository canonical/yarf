*** Settings ***
Resource        kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::tutorial
...    yarf:test_group_id: com.canonical.yarf::integration


*** Test Cases ***
Assert simple counter started
    [Tags]                  yarf:certification_status: blocker
    Match                   ${CURDIR}/simple_counter.png

Increase the counter and assert count
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button on ${CURDIR}/buttons/+.png
    Match Text              Count: 1

Decrease the counter and assert count
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button on ${CURDIR}/buttons/-.png
    Match Text              Count: 0

Toggle theme and assert the theme changed
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button on ${CURDIR}/buttons/toggle_theme.png
    Hid.Move Pointer To Absolute                    x=0                     y=0
    Match                   ${CURDIR}/simple_counter_toggled.png

Close the simple counter
    [Tags]                  yarf:certification_status: blocker
    Keys Combo              Alt_L                   F4

Assert simple counter closed
    [Tags]                  yarf:certification_status: blocker
    Wait Until Keyword Succeeds                     5                       1
    ...                     Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match                   ${CURDIR}/simple_counter_toggled.png            0
