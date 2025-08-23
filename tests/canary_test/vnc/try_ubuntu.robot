*** Settings ***
Resource        kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::canary
...    yarf:test_group_id: com.canonical.yarf::vnc


*** Test Cases ***
Navigate GRUB Menu
    [Tags]                  yarf:certification_status: blocker
    Match Text              GNU GRUB
    Press Key And Match     Down                    ${CURDIR}/01_ubuntu_safe_graphics.png
    Keys Combo              Return

Assert Try Ubuntu Window Started
    [Tags]                  yarf:certification_status: blocker
    Match                   ${CURDIR}/02_language_choosing_screen.png       300

Navigate to Choose Keyboard Screen
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On Next
    Click LEFT Button On Next

Type Sample Text
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On Type here to test your keyboard
    ${sample_text} =        Set Variable            This is a sample text for YARF canary testing.
    Type String             ${sample_text}
    Match Text              ${sample_text}

Try Ubuntu
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On Next
    Click LEFT Button On Next
    Click LEFT Button On ${CURDIR}/03_try_ubuntu.png
    Click LEFT Button On Close

Assert Try Ubuntu Window Closed
    [Tags]                  yarf:certification_status: blocker
    Wait Until Keyword Succeeds                     5                       1
    ...                     Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match                   ${CURDIR}/04_try_ubuntu_window.png              0
