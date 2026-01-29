*** Settings ***
Documentation    Test suite for VideoInput image related keywords.

Resource         kvm.resource

Test Tags
...    robot:stop-on-failure
...    yarf:category_id:com.canonical.yarf::image
...    yarf:test_group_id:com.canonical.yarf::video_input
...    yarf:certification_status:blocker


*** Test Cases ***
Test Keyword Match
    [Documentation]    Test the Match keyword for template matching.
    Match    ${CURDIR}/calculator/01_calculator.png
    Run Keyword And Expect Error    ImageNotFoundError: *
    ...    Match    ${CURDIR}/images/tree.png

Test Keyword Match All
    [Documentation]    Test matching multiple templates at once.
    VAR    @{templates}
    ...    ${CURDIR}/calculator/plus.png
    ...    ${CURDIR}/calculator/minus.png
    ...    ${CURDIR}/calculator/divide.png
    ...    ${CURDIR}/calculator/times.png
    ...    ${CURDIR}/calculator/equals.png
    ${matches}=    Match All    ${templates}
    Length Should Be    ${matches}    5

    VAR    @{templates}
    ...    ${CURDIR}/calculator/equals.png
    ...    ${CURDIR}/images/cloud.png
    Run Keyword And Expect Error    ImageNotFoundError: *
    ...    Match All    ${templates}

Test Keyword Match Any
    [Documentation]    Test matching any of the provided templates.
    VAR    @{templates}
    ...    ${CURDIR}/calculator/equals.png
    ...    ${CURDIR}/images/cloud.png
    ${match}=    Match Any    ${templates}
    Length Should Be    ${match}    1
    Should Be Equal As Strings    ${match[0]['path']}    ${CURDIR}/calculator/equals.png

    VAR    @{templates}
    ...    ${CURDIR}/images/tree.png
    ...    ${CURDIR}/images/cloud.png
    Run Keyword And Expect Error    ImageNotFoundError: *
    ...    Match Any    ${templates}

Test Keyword Get Position Of Target Template
    [Documentation]    Test getting position of a template on screen.
    ${cal_region}=    Match    ${CURDIR}/calculator/01_calculator.png
    VAR    ${equals_template}    ${CURDIR}/calculator/equals.png
    ${x}    ${y}=    Get Position Of ${equals_template}

    Should Be True    ${cal_region}[0][left] < ${x} < ${cal_region}[0][right]
    Should Be True    ${cal_region}[0][top] < ${y} < ${cal_region}[0][bottom]

# Pending on issue: https://warthogs.atlassian.net/browse/YARF-57
# Test Keyword Restart Video Input
#    [Tags]    yarf:certification_status:blocker
#    Restart Video Input
#    Sleep    2s
#    Match    ${CURDIR}/calculator/01_calculator.png

Test Keyword Log Screenshot
    [Documentation]    Test the Log Screenshot keyword.
    Log Screenshot    This is a test screenshot
