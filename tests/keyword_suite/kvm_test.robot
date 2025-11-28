*** Settings ***
Documentation       This suite tests KVM keywords under kvm.resource.

Resource            kvm.resource

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

Test Keyword Move Pointer To Destination In Domain
    [Tags]                  yarf:certification_status: blocker
    ${cal_region}=          Match                   ${CURDIR}/calculator/01_calculator.png
    ${x}                    ${y}=                   Move Pointer To 1 In ${cal_region}[0]

    Should Be True          ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True          ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]

    ${x}                    ${y}=                   Move Pointer To ${CURDIR}/calculator/equals.png In ${cal_region}[0]

    Should Be True          ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True          ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]
