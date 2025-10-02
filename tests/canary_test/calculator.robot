*** Settings ***
Resource        kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::canary
...    yarf:test_group_id: com.canonical.yarf::canary


*** Test Cases ***
Assert Calculator Started
    [Tags]                  yarf:certification_status: blocker
    Match                   ${CURDIR}/01_calculator.png

Answer the ultimate question of life, the universe and everything
    [Tags]                  yarf:certification_status: blocker
    Click LEFT Button On 1
    Click LEFT Button On 0
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
