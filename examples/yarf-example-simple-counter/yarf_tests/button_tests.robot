*** Settings ***
Documentation    Test suite for simple counter application button interactions.
Resource         kvm.resource

Test Tags
...    robot:stop-on-failure
...    yarf:category_id:com.canonical.yarf::tutorial
...    yarf:test_group_id:com.canonical.yarf::integration
...    yarf:certification_status:blocker


*** Test Cases ***
Assert Simple Counter Started
    [Documentation]    Verify the simple counter application has started.
    Match    ${CURDIR}/simple_counter.png

Increase The Counter And Assert Count
    [Documentation]    Click the plus button and verify the count increases.
    Click LEFT Button On    ${CURDIR}/buttons/+.png
    Match Text    Count: 1

Decrease The Counter And Assert Count
    [Documentation]    Click the minus button and verify the count decreases.
    Click LEFT Button On    ${CURDIR}/buttons/-.png
    Match Text    Count: 0

Toggle Theme And Assert The Theme Changed
    [Documentation]    Toggle the application theme and verify the change.
    Click LEFT Button On    ${CURDIR}/buttons/toggle_theme.png
    Hid.Move Pointer To Absolute    x=0    y=0
    Match    ${CURDIR}/simple_counter_toggled.png

Close The Simple Counter
    [Documentation]    Close the simple counter application.
    Keys Combo    Alt_L    F4

Assert Simple Counter Closed
    [Documentation]    Verify the simple counter application has closed.
    Wait Until Keyword Succeeds    5    1
    ...    Run Keyword And Expect Error    ImageNotFoundError: *
    ...    Match    ${CURDIR}/simple_counter_toggled.png    0
