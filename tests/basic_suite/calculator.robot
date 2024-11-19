*** Settings ***
Resource        kvm.resource

Task Tags       robot:stop-on-failure


*** Test Cases ***
Assert Calculator Started
    Match                   ${CURDIR}/01_calculator.png

Answer the ultimate question of life, the universe and everything
    Click LEFT Button on ${CURDIR}/calculator/1.png
    Click LEFT Button on ${CURDIR}/calculator/0.png
    Click LEFT Button on ${CURDIR}/calculator/x.png
    Type String             4+2=

Assert correct Answer
    Match                   ${CURDIR}/02_answer.png

Close the calculator
    Keys Combo              Alt_L                   F4

Assert calculator closed
    Wait Until Keyword Succeeds                     5                       1
    ...                     Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match                   ${CURDIR}/02_answer.png                         0
