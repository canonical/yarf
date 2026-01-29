*** Settings ***
Documentation    Test suite for VideoInput text related keywords.

Library          String
Resource         kvm.resource

Test Tags
...    robot:stop-on-failure
...    yarf:category_id:com.canonical.yarf::text
...    yarf:test_group_id:com.canonical.yarf::video_input
...    yarf:certification_status:blocker


*** Variables ***
${SAMPLE_TEXT}
...    Lorem ipsum dolor sit amet consectetur adipiscing elit.
...    Quisque faucibus ex sapien vitae pellentesque sem placerat.
...    In id cursus mi pretium tellus duis convallis.
...    Tempus leo eu aenean sed diam urna tempor.
...    Pulvinar vivamus fringilla lacus nec metus bibendum egestas.
...    Iaculis massa nisl malesuada lacinia integer nunc posuere.
...    Ut hendrerit semper vel class aptent taciti sociosqu.
...    Ad litora torquent per conubia nostra inceptos himenaeos.
&{SAMPLE_TEXT_REGION}       left=420    top=417    right=851    bottom=600
${REGEX}                    ([A-W]{2}[0-9O]{3}[a-z]{2})
&{REGEX_REGION}             left=50    top=50    right=370    bottom=140


*** Test Cases ***
Test Text Keywords With Rapid Ocr
    [Documentation]    Test OCR keywords using RapidOCR engine.
    Set Ocr Method    rapidocr
    Test Keyword Read Text
    Test Keyword Get Text Position
    Test Keyword Get Position Of Target String
    Test Keyword Find Text
    Test Keyword Match Text

Test Text Keywords With Tesseract
    [Documentation]    Test OCR keywords using Tesseract engine.
    Set Ocr Method    tesseract
    Test Keyword Read Text
    Test Keyword Get Text Position
    Test Keyword Get Position Of Target String
    Test Keyword Find Text
    Test Keyword Match Text

Test Set Ocr Method With Invalid Method
    [Documentation]    Test that invalid OCR method raises an error.
    Run Keyword And Expect Error    ValueError: *
    ...    Set Ocr Method    invalid


*** Keywords ***
Test Keyword Read Text
    [Documentation]    Test reading text from an image.
    ${text}=    Read Text    ${CURDIR}/text/sample_text.png
    ${text}=    Replace String    ${text}    \r\n    \n
    ${text}=    Replace String Using Regexp
    ...    ${text}
    ...    [\r\n\t]+
    ...    ${SPACE}
    ${text}=    Strip String    ${text}
    ${ratio}=    Evaluate
    ...    difflib.SequenceMatcher(None, """${text}""", """${SAMPLE_TEXT}""").ratio()
    ...    modules=difflib
    Log    Similarity ratio = ${ratio}
    Should Be True    ${ratio} >= ${DEFAULT_TEMPLATE_MATCHING_TOLERANCE}

Test Keyword Get Text Position
    [Documentation]    Test getting position of specific text.
    ${x}    ${y}=    Get Text Position
    ...    tempor
    ...    ${SAMPLE_TEXT_REGION}
    Should Be True    582 <= ${x} <= 640
    Should Be True    485 <= ${y} <= 510

Test Keyword Get Position Of Target String
    [Documentation]    Test getting position of a target string.
    VAR    ${target_text}    tempor
    ${x}    ${y}=    Get Position Of ${target_text}
    Should Be True    582 <= ${x} <= 640
    Should Be True    485 <= ${y} <= 510

Test Keyword Find Text
    [Documentation]    Test finding text with exact and regex matching.
    Test Find Text Exact Match
    Test Find Text Regex Match
    Test Find Text No Match

Test Find Text Exact Match
    [Documentation]    Test finding exact text match.
    ${matched_text}=    Find Text    AB123cd    region=${REGEX_REGION}
    ${length}=    Get Length    ${matched_text}
    Should Be True    ${length} > 1
    Should Be Equal As Strings    ${matched_text[0]['text']}    AB123cd
    Should Be Equal As Numbers    ${matched_text[0]['Similarity']}    100.0

Test Find Text Regex Match
    [Documentation]    Test finding text with regex pattern.
    ${matched_text}=    Find Text    regex:${REGEX}    region=${REGEX_REGION}
    VAR    ${count}    0
    # Note: 0 <--> O is a common mis-recognition
    ${expected_text}=    Evaluate    {"AB123cd", "RK001xy", "RKOO1xy"}
    FOR    ${match}    IN    @{matched_text}
        VAR    ${text}    ${match['text']}
        IF    '${text}' in ${expected_text}
            ${count}=    Evaluate    ${count} + 1
        END
    END
    Should Be Equal As Integers    ${count}    2

Test Find Text No Match
    [Documentation]    Test finding text that doesn't exist.
    ${matched_text}=    Find Text    not_expected    region=${REGEX_REGION}
    Should Be Empty    ${matched_text}

Test Keyword Match Text
    [Documentation]    Test matching text with exact and regex patterns.
    Test Match Text Exact
    Test Match Text Regex
    Test Match Text Error

Test Match Text Exact
    [Documentation]    Test exact text matching.
    ${region}=    Catenate
    ...    SEPARATOR=,
    ...    ${REGEX_REGION.left}
    ...    ${REGEX_REGION.top}
    ...    ${REGEX_REGION.right}
    ...    ${REGEX_REGION.bottom}

    ${matches}    ${_}=    Match Text
    ...    AB123cd
    ...    region=${region}
    ${length}=    Get Length    ${matches}
    Should Be True    ${length} > 1

Test Match Text Regex
    [Documentation]    Test regex text matching.
    ${region}=    Catenate
    ...    SEPARATOR=,
    ...    ${REGEX_REGION.left}
    ...    ${REGEX_REGION.top}
    ...    ${REGEX_REGION.right}
    ...    ${REGEX_REGION.bottom}

    ${matches}    ${_}=    Match Text
    ...    regex:${REGEX}
    ...    region=${region}
    VAR    ${count}    0
    ${expected_text}=    Evaluate    {"AB123cd", "RK001xy", "RKOO1xy"}
    FOR    ${match}    IN    @{matches}
        VAR    ${text}    ${match['text']}
        IF    '${text}' in ${expected_text}
            ${count}=    Evaluate    ${count} + 1
        END
    END
    Should Be Equal As Integers    ${count}    2

Test Match Text Error
    [Documentation]    Test that non-matching text raises an error.
    ${region}=    Catenate
    ...    SEPARATOR=,
    ...    ${REGEX_REGION.left}
    ...    ${REGEX_REGION.top}
    ...    ${REGEX_REGION.right}
    ...    ${REGEX_REGION.bottom}

    Run Keyword And Expect Error    ValueError: *
    ...    Match Text    not_expected    region=${region}
