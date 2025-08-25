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
    Keys Combo              Return

Assert Try Ubuntu Window Started
    [Tags]                  yarf:certification_status: blocker
    @{templates}=           Create List
    ...                     ${CURDIR}/01_language_choosing_screen.png
    ...                     ${CURDIR}/01_search_bar.png
    ${result}=              Match Any               ${templates}            300
    IF    '${result}[0][path]'=='${CURDIR}/01_search_bar.png'
        Press Key And Match     Escape                  ${CURDIR}/01_language_choosing_screen.png       180
    END
    Match                   ${CURDIR}/01_language_choosing_screen.png
    Sleep                   2s

Navigate to Choose Keyboard Screen
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On Next
    Click LEFT Button On Next
    Sleep                   2s

Type Sample Text
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On Type here to test your keyboard
    ${sample_text}=         Set Variable            This is a sample text for YARF canary testing.
    Type String             ${sample_text}
    Match Text              ${sample_text}
    Sleep                   2s

Try Ubuntu
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On Next
    Click LEFT Button On Next
    Click LEFT Button On ${CURDIR}/02_try_ubuntu.png
    Click LEFT Button On Close

Assert Try Ubuntu Window Closed
    [Tags]                  yarf:certification_status: blocker
    Wait Until Keyword Succeeds                     5                       1
    ...                     Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match                   ${CURDIR}/03_try_ubuntu_window.png              0
