*** Settings ***
Documentation       This suite tests VideoInput image related keywords.

Resource            kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::image
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Test Cases ***
Test Keyword Match
    [Tags]                  yarf:certification_status: blocker
    Match                   ${CURDIR}/calculator/01_calculator.png
    Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match                   ${CURDIR}/images/tree.png

Test Keyword Match All
    [Tags]                  yarf:certification_status: blocker
    ${matches}=             Match All
    ...                     ${CURDIR}/calculator/plus.png
    ...                     ${CURDIR}/calculator/minus.png
    ...                     ${CURDIR}/calculator/divide.png
    ...                     ${CURDIR}/calculator/times.png
    ...                     ${CURDIR}/calculator/equals.png
    Length Should Be        ${matches}              5
    Run Keyword And Expect Error
    ...                     ImageNotFoundError: *
    ...                     Match All
    ...                     ${CURDIR}/calculator/equals.png
    ...                     ${CURDIR}/images/cloud.png

Test Keyword Match Any
    [Tags]                  yarf:certification_status: blocker
    ${match}=               Match Any
    ...                     ${CURDIR}/calculator/equals.png
    ...                     ${CURDIR}/images/cloud.png
    Length Should Be        ${match}                1
    Should Be Equal As Strings                      ${match[0]['path']}     ${CURDIR}/calculator/equals.png

    Run Keyword And Expect Error
    ...                     ImageNotFoundError: *
    ...                     Match Any
    ...                     ${CURDIR}/images/tree.png
    ...                     ${CURDIR}/images/cloud.png

Test Keyword Restart Video Input
    [Tags]                  yarf:certification_status: blocker
    Restart Video Input
    Match                   ${CURDIR}/calculator/01_calculator.png
