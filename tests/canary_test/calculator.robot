*** Settings ***
Documentation    Test suite for calculator application interactions.
Resource         kvm.resource

Test Tags
...    robot:stop-on-failure
...    yarf:category_id:com.canonical.yarf::canary
...    yarf:test_group_id:com.canonical.yarf::canary
...    yarf:certification_status:blocker


*** Test Cases ***
Assert Calculator Started
    [Documentation]    Verify the calculator application has started.
    Match    ${CURDIR}/01_calculator.png

Answer The Ultimate Question Of Life The Universe And Everything
    [Documentation]    Calculate the answer to the ultimate question.
    Click Left Button On 1
    Click Left Button On 0
    Click Left Button On    ${CURDIR}/calculator/x.png
    Type String    4+2\=

Assert Correct Answer
    [Documentation]    Verify the calculation result is correct.
    Match    ${CURDIR}/02_answer.png

Close The Calculator
    [Documentation]    Close the calculator application.
    Keys Combo    Alt_L    F4

Assert Calculator Closed
    [Documentation]    Verify the calculator application has closed.
    Wait Until Keyword Succeeds    5    1
    ...    Run Keyword And Expect Error    ImageNotFoundError: *
    ...    Match    ${CURDIR}/02_answer.png    0
