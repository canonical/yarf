*** Settings ***
Documentation       This suite tests VideoInput text related keywords.

Resource            kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::text
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Variables ***
${SAMPLE_TEXT}              Lorem ipsum dolor sit amet consectetur adipiscing elit. Quisque faucibus ex sapien vitae pellentesque sem placerat. In id cursus mi pretium tellus duis convallis. Tempus leo eu aenean sed diam urna tempor. Pulvinar vivamus fringilla lacus nec metus bibendum egestas. Iaculis massa nisl malesuada lacinia integer nunc posuere. Ut hendrerit semper vel class aptent taciti sociosqu. Ad litora torquent per conubia nostra inceptos himenaeos.
&{SAMPLE_TEXT_REGION}       left=420    top=417    right=851    bottom=600
${REGEX}                    ^[A-Z]{2}[0-9]{3}[a-z]{2}$
&{REGEX_REGION}             left=50    top=50    right=370    bottom=140


*** Test Cases ***
Test Text Keywords with Rapid Ocr
    [Tags]                  yarf:certification_status: blocker
    Set Ocr Method          rapidocr
    Test Keyword Read Text
    Test Keyword Get Text Position
    Test Keyword Find Text
    Test Keyword Match Text

Test Text Keywords with Tesseract
    [Tags]                  yarf:certification_status: blocker
    Set Ocr Method          tesseract
    Test Keyword Read Text
    Test Keyword Get Text Position
    Test Keyword Find Text
    Test Keyword Match Text

Test Set Ocr Method with Invalid Method
    [Tags]                  yarf:certification_status: blocker
    Run Keyword And Expect Error                    ValueError: *
    ...                     Set Ocr Method          invalid


*** Keywords ***
Test Keyword Read Text
    [Tags]                  yarf:certification_status: blocker
    ${text}=                Read Text               ${SAMPLE_TEXT}
    Should Be Equal As Strings                      ${text}                 ${SAMPLE_TEXT}

Test Keyword Get Text Position
    [Tags]                  yarf:certification_status: blocker
    ${position}=            Get Text Position       ${SAMPLE_TEXT}          ${SAMPLE_TEXT_REGION}
    Should Be Equal         ${position}             ${636,_509}

Test Keyword Find Text
    [Tags]                  yarf:certification_status: blocker
    ${matched_text}=        Find Text               AB123cd                 region=${REGEX_REGION}
    Length Should Be        ${matched_text}         1

    ${matched_text}=        Find Text               regex:${REGEX}          region=${REGEX_REGION}
    ${count}=               Set Variable            0
    ${expected_text}=       Evaluate                {"AB123cd", "XY999zz", "RK001xy"}
    FOR    ${match}    IN    @{matched_text}
        ${text}=                Set Variable            ${match['text']}
        IF    '${text}' in ${expected_text}
            ${count}=               Evaluate                ${count} + 1
        END
    END
    Should Be Equal As Integers                     ${count}                3

    ${matched_text}=        Find Text               not_expected            region=${REGEX_REGION}
    Should Be Empty         ${matched_text}

Test Keyword Match Text
    [Tags]                  yarf:certification_status: blocker
    ${region}=              Catenate
    ...                     SEPARATOR=,
    ...                     ${REGEX_REGION.left}
    ...                     ${REGEX_REGION.top}
    ...                     ${REGEX_REGION.right}
    ...                     ${REGEX_REGION.bottom}

    ${matches}              ${image}=               Match Text
    ...                     AB123cd
    ...                     region=${REGEX_REGION}
    Length Should Be        ${matches}              1
    Should Not Be Empty     ${image}

    ${matches}              ${image}=               Match Text
    ...                     regex:${REGEX}
    ...                     region=${REGEX_REGION}
    ${count}=               Set Variable            0
    ${expected_text}=       Evaluate                {"AB123cd", "XY999zz", "RK001xy"}
    FOR    ${match}    IN    @{MATCHED_TEXT}
        ${text}=                Set Variable            ${match['text']}
        IF    '${text}' in ${expected_text}
            ${count}=               Evaluate                ${count} + 1
        END
    END
    Should Be Equal As Integers                     ${count}                3

    ${matches}              ${image}=               Match Text
    ...                     not_expected
    ...                     region=${REGEX_REGION}
    Should Be Empty         ${matches}
