*** Settings ***
Documentation       This suite tests VideoInput text related keywords.

Library             String
Resource            kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::text
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Variables ***
${SAMPLE_TEXT}              Lorem ipsum dolor sit amet consectetur adipiscing elit. Quisque faucibus ex sapien vitae pellentesque sem placerat. In id cursus mi pretium tellus duis convallis. Tempus leo eu aenean sed diam urna tempor. Pulvinar vivamus fringilla lacus nec metus bibendum egestas. Iaculis massa nisl malesuada lacinia integer nunc posuere. Ut hendrerit semper vel class aptent taciti sociosqu. Ad litora torquent per conubia nostra inceptos himenaeos.
&{SAMPLE_TEXT_REGION}       left=420    top=417    right=851    bottom=600
${REGEX}                    ([A-W]{2}[0-9O]{3}[a-z]{2})
&{REGEX_REGION}             left=50    top=50    right=370    bottom=140


*** Test Cases ***
Test Text Keywords with Rapid Ocr
    [Tags]                  yarf:certification_status: blocker
    Set Ocr Method          rapidocr
    Test Keyword Read Text
    Test Keyword Get Text Position
    Test Keyword Get Position Of Target String
    Test Keyword Find Text
    Test Keyword Match Text

Test Text Keywords with Tesseract
    [Tags]                  yarf:certification_status: blocker
    Set Ocr Method          tesseract
    Test Keyword Read Text
    Test Keyword Get Text Position
    Test Keyword Get Position Of Target String
    Test Keyword Find Text
    Test Keyword Match Text

Test Set Ocr Method with Invalid Method
    [Tags]                  yarf:certification_status: blocker
    Run Keyword And Expect Error                    ValueError: *
    ...                     Set Ocr Method          invalid


*** Keywords ***
Test Keyword Read Text
    [Tags]                  yarf:certification_status: blocker
    ${text}=                Read Text               ${CURDIR}/text/sample_text.png
    ${text}=                Replace String          ${text}                 \r\n                    \n
    ${text}=                Replace String Using Regexp
    ...                     ${text}
    ...                     [\r\n\t]+
    ...                     ${SPACE}
    ${text}=                Strip String            ${text}
    ${ratio}=               Evaluate
    ...                     difflib.SequenceMatcher(None, """${text}""", """${SAMPLE_TEXT}""").ratio()
    ...                     modules=difflib
    Log                     Similarity ratio = ${ratio}
    Should Be True          ${ratio} >= ${DEFAULT_TEMPLATE_MATCHING_TOLERANCE}

Test Keyword Get Text Position
    [Tags]                  yarf:certification_status: blocker
    ${x}                    ${y}=                   Get Text Position
    ...                     tempor
    ...                     ${SAMPLE_TEXT_REGION}
    Should Be True          582 <= ${x} <= 640
    Should Be True          485 <= ${y} <= 510

Test Keyword Get Position Of Target String
    [Tags]                  yarf:certification_status: blocker
    ${x}                    ${y}=                   Get Position Of tempor
    Should Be True          582 <= ${x} <= 640
    Should Be True          485 <= ${y} <= 510

Test Keyword Find Text
    [Tags]                  yarf:certification_status: blocker
    ${matched_text}=        Find Text               AB123cd                 region=${REGEX_REGION}
    ${length}=              Get Length              ${matched_text}
    Should Be True          ${length} > 1
    Should Be Equal As Strings                      ${matched_text[0]['text']}                      AB123cd
    Should Be Equal As Numbers                      ${matched_text[0]['similarity']}                100.0

    ${matched_text}=        Find Text               regex:${REGEX}          region=${REGEX_REGION}
    ${count}=               Set Variable            0
    # Note: 0 <--> O is a common mis-recognition
    ${expected_text}=       Evaluate                {"AB123cd", "RK001xy", "RKOO1xy"}
    FOR    ${match}    IN    @{matched_text}
        ${text}=                Set Variable            ${match['text']}
        IF    '${text}' in ${expected_text}
            ${count}=               Evaluate                ${count} + 1
        END
    END
    Should Be Equal As Integers                     ${count}                2

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
    ...                     region=${region}
    ${length}=              Get Length              ${matches}
    Should Be True          ${length} > 1
    ${is_image}=            Evaluate                isinstance($image, __import__('PIL.Image').Image.Image)
    Should Be True          ${is_image}

    ${matches}              ${image}=               Match Text
    ...                     regex:${REGEX}
    ...                     region=${region}
    ${count}=               Set Variable            0
    ${expected_text}=       Evaluate                {"AB123cd", "RK001xy", "RKOO1xy"}
    FOR    ${match}    IN    @{matches}
        ${text}=                Set Variable            ${match['text']}
        IF    '${text}' in ${expected_text}
            ${count}=               Evaluate                ${count} + 1
        END
    END
    Should Be Equal As Integers                     ${count}                2

    Run Keyword And Expect Error                    ValueError: *
    ...                     Match Text              not_expected            region=${region}
