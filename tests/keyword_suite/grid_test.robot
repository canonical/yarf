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
# --variable CONTRAST:0.4 --variable COLOR_TOLERANCE:10
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
    Press Right Until tiger Is Highlighted          color_tolerance=${COLOR_TOLERANCE}
    ${on_target}=           Is Highlighted Text     tiger                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_target}
    ${on_start}=            Is Highlighted Text     apple                   color_tolerance=${COLOR_TOLERANCE}
    Should Not Be True      ${on_start}

Press Keys Until Target Is Highlighted Walks A Column
    [Documentation]    Press Keys Until ${target} Is Highlighted presses a
    ...    sequence of Down keys to walk down a column, then a single Up to
    ...    step back up one row.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until apple Is Highlighted          color_tolerance=${COLOR_TOLERANCE}
    Press Keys Until quilt Is Highlighted           ${{ ['Down'] * 6 }}     color_tolerance=${COLOR_TOLERANCE}
    ${on_bottom}=           Is Highlighted Text     quilt                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_bottom}
    Press Keys Until joker Is Highlighted           ${{ ['Up'] }}           color_tolerance=${COLOR_TOLERANCE}
    ${on_up}=               Is Highlighted Text     joker                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_up}

Press Keys Until Target Is Highlighted Walks A Diagonal
    [Documentation]    Press Keys Until ${target} Is Highlighted presses the
    ...    given sequence of keys, so a repeated Down + Right walks the
    ...    highlight along the grid diagonal to the target.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until apple Is Highlighted          color_tolerance=${COLOR_TOLERANCE}
    Press Keys Until glide Is Highlighted           ${{ ['Down', 'Right'] * 4 }}                    color_tolerance=${COLOR_TOLERANCE}
    ${on_target}=           Is Highlighted Text     glide                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_target}

Enter Selects And Escape Clears The Selection
    [Documentation]    Enter turns the highlighted word green; Escape clears
    ...    every green selection. Highlight detection is row-based, so the
    ...    highlight is moved to a different row (Up) to tell the selected row
    ...    apart from the highlighted one.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until wheat Is Highlighted          color_tolerance=${COLOR_TOLERANCE}
    Keys Combo              Return
    ${selected}=            Is Highlighted Text     wheat                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${selected}
    Keys Combo              Up
    Keys Combo              Escape
    Sleep                   0.3
    ${cleared}=             Is Highlighted Text     wheat                   color_tolerance=${COLOR_TOLERANCE}
    Should Not Be True      ${cleared}
    ${on_neighbour}=        Is Highlighted Text     joker                   color_tolerance=${COLOR_TOLERANCE}
    Should Be True          ${on_neighbour}

Close The Word Grid
    [Documentation]    Close the application.
    [Tags]                  yarf:certification_status: blocker
    Keys Combo              Alt_L                   F4


*** Keywords ***
Start Word Grid
    [Documentation]    Starts the word grid application at ${CONTRAST} contrast
    ...    and waits for it to be open with the top-left word displayed.
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
