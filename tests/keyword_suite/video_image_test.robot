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
    ${templates}=           Create List
    ...                     ${CURDIR}/calculator/plus.png
    ...                     ${CURDIR}/calculator/minus.png
    ...                     ${CURDIR}/calculator/divide.png
    ...                     ${CURDIR}/calculator/times.png
    ...                     ${CURDIR}/calculator/equals.png
    ${matches}=             Match All               ${templates}
    Length Should Be        ${matches}              5

    ${templates}=           Create List
    ...                     ${CURDIR}/calculator/equals.png
    ...                     ${CURDIR}/images/cloud.png
    Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match All               ${templates}

Test Keyword Match Any
    [Tags]                  yarf:certification_status: blocker
    ${templates}=           Create List
    ...                     ${CURDIR}/calculator/equals.png
    ...                     ${CURDIR}/images/cloud.png
    ${match}=               Match Any               ${templates}
    Length Should Be        ${match}                1
    Should Be Equal As Strings                      ${match[0]['path']}     ${CURDIR}/calculator/equals.png

    ${templates}=           Create List
    ...                     ${CURDIR}/images/tree.png
    ...                     ${CURDIR}/images/cloud.png
    Run Keyword And Expect Error                    ImageNotFoundError: *
    ...                     Match Any               ${templates}

Test Keyword Get Position Of Target Template
    [Tags]                  yarf:certification_status: blocker
    ${cal_region}=          Match                   ${CURDIR}/calculator/01_calculator.png
    ${x}                    ${y}=                   Get Position Of ${CURDIR}/calculator/equals.png

    Should Be True          ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True          ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]

# Pending on issue: https://warthogs.atlassian.net/browse/YARF-57
# Test Keyword Restart Video Input
#    [Tags]    yarf:certification_status: blocker
#    Restart Video Input
#    Sleep    2s
#    Match    ${CURDIR}/calculator/01_calculator.png
