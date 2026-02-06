*** Settings ***
Documentation       This suite tests KVM keywords under kvm.resource.

Library             Process
Library             Collections
Resource            kvm.resource

Suite Setup         Start Calculator

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::kvm
...    yarf:test_group_id: com.canonical.yarf::kvm


*** Test Cases ***
Test Keyword Displace Point By X Y
    [Tags]                  yarf:certification_status: blocker
    ${result}=              Displace ${3,3} By (5, 5)
    Should Be True          ${result} == (8, 8)

Test Keyword Ensure Destination Does Not Match
    [Tags]                  yarf:certification_status: blocker
    Ensure string Does Not Match
    Ensure ${CURDIR}/images/cloud.png Does Not Match

Test Keyword Press Key And Match
    [Tags]                  yarf:certification_status: blocker
    Type String             10*4+2
    Press Key And Match     Return                  ${CURDIR}/calculator/02_answer.png

Test Keyword Press And Wait For Match
    [Tags]                  yarf:certification_status: blocker
    ${combo}=               Create List             Control_L               Escape
    Press And Wait For Match                        ${combo}                ${CURDIR}/calculator/03_answer_escaped.png

Test Keyword Move Pointer To Destination In Domain
    [Tags]                  yarf:certification_status: blocker
    ${cal_region}=          Match                   ${CURDIR}/calculator/01_calculator.png
    ${target_region}=       Set Variable            ${cal_region}[0]
    Remove From Dictionary                          ${target_region}        path

    ${x}                    ${y}=                   Move Pointer To 1 In ${target_region}

    Should Be True          ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True          ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]

    ${x}                    ${y}=                   Move Pointer To ${CURDIR}/calculator/equals.png In ${target_region}

    Should Be True          ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True          ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]


*** Keywords ***
Start Calculator
    [Documentation]    Starts the calculator application.
    Start Process
    ...                     dbus-run-session
    ...                     --
    ...                     gnome-calculator
