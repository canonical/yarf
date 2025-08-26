*** Settings ***
Resource        kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::canary
...    yarf:test_group_id: com.canonical.yarf::vnc


*** Test Cases ***
Assert Calculator Started
    [Tags]                  yarf:certification_status: blocker
    Match                   ${CURDIR}/01_calculator.png
    Match Text              Basic

Answer the ultimate question of life, the universe and everything
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On ${CURDIR}/calculator/1.png
    Click LEFT Button On ${CURDIR}/calculator/0.png
    Click LEFT Button on ${CURDIR}/calculator/x.png
    Type String             4+2=

Assert correct Answer
    [Tags]                  yarf:certification_status: blocker
    Match                   ${CURDIR}/02_answer.png

Close the calculator
    [Tags]                  yarf:certification_status: blocker
    Keys Combo              Alt_L                   F4

Assert calculator closed
    [Tags]                  yarf:certification_status: blocker
    Wait Until Keyword Succeeds                     5                       1
    ...                     Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match                   ${CURDIR}/02_answer.png                         0
