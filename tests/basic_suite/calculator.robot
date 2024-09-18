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
    Click LEFT Button on ${CURDIR}/calculator/4.png
    Click LEFT Button on ${CURDIR}/calculator/+.png
    Click LEFT Button on ${CURDIR}/calculator/2.png
    Click LEFT Button on ${CURDIR}/calculator/=.png

Assert correct Answer
    Match                   ${CURDIR}/02_answer.png
