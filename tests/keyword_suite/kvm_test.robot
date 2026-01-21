*** Settings ***
Documentation    Test suite for KVM keywords under kvm.resource.

Library          Collections
Resource         kvm.resource

Test Tags
...    robot:stop-on-failure
...    yarf:category_id:com.canonical.yarf::kvm
...    yarf:test_group_id:com.canonical.yarf::kvm
...    yarf:certification_status:blocker


*** Test Cases ***
Test Keyword Displace Point By X Y
    [Documentation]    Test the Displace keyword with coordinates.
    ${result}=    Displace ${3,3} By (5, 5)
    Should Be True    ${result} == (8, 8)

Test Keyword Ensure Destination Does Not Match
    [Documentation]    Test that non-matching templates are correctly identified.
    VAR    ${test_string}    string
    Ensure ${test_string} Does Not Match
    VAR    ${cloud_template}    ${CURDIR}/images/cloud.png
    Ensure ${cloud_template} Does Not Match

Test Keyword Press Key And Match
    [Documentation]    Test pressing a key and matching the result.
    Type String    10*4+2
    Press Key And Match    Return    ${CURDIR}/calculator/02_answer.png

Test Keyword Press And Wait For Match
    [Documentation]    Test pressing a key combo and waiting for match.
    VAR    @{combo}    Control_L    Escape
    Press And Wait For Match    ${combo}    ${CURDIR}/calculator/03_answer_escaped.png

Test Keyword Move Pointer To Destination In Domain
    [Documentation]    Test moving the pointer within a constrained domain.
    ${cal_region}=    Match    ${CURDIR}/calculator/01_calculator.png
    VAR    ${target_region}    ${cal_region}[0]
    Remove From Dictionary    ${target_region}    path

    ${x}    ${y}=    Move Pointer To 1 In ${target_region}

    Should Be True    ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True    ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]

    VAR    ${equals_template}    ${CURDIR}/calculator/equals.png
    ${x}    ${y}=    Move Pointer To ${equals_template} In ${target_region}

    Should Be True    ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True    ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]
