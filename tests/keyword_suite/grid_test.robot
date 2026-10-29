*** Settings ***
Documentation       This suite tests keyboard-only navigation of a word grid
...                 using the highlight-detection keywords (Get Highlighted
...                 Text / Is Highlighted Text) and the Press ... Until ...
...                 Is Highlighted keywords.

Library             Process
Resource            kvm.resource

Suite Setup         Start Word Grid

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::grid
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Variables ***
# Contrast of the highlight relative to the background (0..1) and the matching
# background colour tolerance used for detection. Override to exercise a
# low-contrast highlight, e.g.
# --variable CONTRAST:0.55 --variable COLOR_TOLERANCE:10
${CONTRAST}             0.85
${COLOR_TOLERANCE}      20


*** Test Cases ***
Grid Starts With Top Left Highlighted
    [Documentation]    The top-left word is highlighted when the grid opens.
    [Tags]                  yarf:certification_status: blocker
    ${highlighted}=         Is Highlighted Text     apple                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${highlighted}

Press Button Until Target Is Highlighted Moves The Highlight
    [Documentation]    Press ${button} Until ${target} Is Highlighted moves the
    ...    highlight onto the target word.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until flame Is Highlighted          color_tolerance=${COLOR_TOLERANCE}
    ${on_target}=           Is Highlighted Text     flame                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_target}
    ${on_start}=            Is Highlighted Text     apple                   color_tolerance=${COLOR_TOLERANCE}
    Should Not Be True      ${on_start}

Press Keys Until Target Is Highlighted Walks A Column
    [Documentation]    Press Keys Until ${target} Is Highlighted presses a
    ...    sequence of Down keys to walk down a column, then a single Up to
    ...    step back up one row.
    [Tags]                  yarf:certification_status: blocker
    Press Keys Until vapor Is Highlighted           ${{ ['Down'] * 6 }}     color_tolerance=${COLOR_TOLERANCE}
    ${on_bottom}=           Is Highlighted Text     vapor                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_bottom}
    Press Keys Until olive Is Highlighted           ${{ ['Up'] }}           color_tolerance=${COLOR_TOLERANCE}
    ${on_up}=               Is Highlighted Text     olive                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_up}

Press Keys Until Target Is Highlighted Walks A Diagonal
    [Documentation]    Press Keys Until ${target} Is Highlighted presses the
    ...    given sequence of keys, so a repeated Down + Right walks the
    ...    highlight along the grid diagonal to the target.
    [Tags]                  yarf:certification_status: blocker
    Press Keys Until ivory Is Highlighted           ${{ ['Left', 'Up'] * 4 }}                       color_tolerance=${COLOR_TOLERANCE}
    ${on_target}=           Is Highlighted Text     ivory                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_target}

Close The Word Grid
    [Documentation]    Close the application.
    [Tags]                  yarf:certification_status: blocker
    Keys Combo              Alt_L                   F4


*** Keywords ***
Start Word Grid
    [Documentation]    Starts the word grid application at ${CONTRAST} contrast
    ...    and waits for it to be open with the top-left word displayed.
    # RapidOCR reports a box per word, so each cell is a separate region and a
    # single highlighted cell stands out cleanly (Tesseract would merge a whole
    # row into one region and average the highlight away).
    Set Ocr Method          rapidocr
    Start Process
    ...                     dbus-run-session
    ...                     --
    ...                     uv
    ...                     --project
    ...                     ${CURDIR}/grid
    ...                     run
    ...                     grid-app
    ...                     --contrast
    ...                     ${CONTRAST}
    Match Text              apple                   timeout=90
