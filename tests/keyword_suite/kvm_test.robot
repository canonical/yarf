*** Settings ***
Documentation       This suite tests KVM keywords under kvm.resource.

Resource            kvm.resource
Resource            ../../.tox/py310/lib/python3.10/site-packages/yarf/rf_libraries/resources/kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::kvm
...    yarf:test_group_id: com.canonical.yarf::kvm


*** Test Cases ***
Test Keyword Displace Point By X Y
    [Tags]                  yarf:certification_status: blocker
    ${result}=              Displace                ${3,_3} By (5, 5)
    Should Be True          ${REUSLT} == (8, 8)

Test Keyword Ensure Destination Des Not Match
    [Tags]                  yarf:certification_status: blocker
    Ensure string Does Not Match
    Ensure ${CURDIR}/images/cloud.png Does Not Match
