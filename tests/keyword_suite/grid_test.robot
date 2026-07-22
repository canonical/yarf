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


*** Test Cases ***
Grid Starts With Top Left Highlighted
    [Documentation]    The top-left word is highlighted when the grid opens.
    [Tags]                  yarf:certification_status: blocker
    ${highlighted}=         Is Highlighted Text     apple
    Should Be True          ${highlighted}

Press Button Until Target Is Highlighted Moves The Highlight
    [Documentation]    Press ${button} Until ${target} Is Highlighted moves the
    ...    highlight onto the target word.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until tiger Is Highlighted
    ${on_target}=           Is Highlighted Text     tiger
    Should Be True          ${on_target}
    ${on_start}=            Is Highlighted Text     apple
    Should Not Be True      ${on_start}

Press Keys Until Target Is Highlighted Walks A Column
    [Documentation]    Press Keys Until ${target} Is Highlighted presses a
    ...    sequence of Down keys to walk down a column, then a single Up to
    ...    step back up one row.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until apple Is Highlighted
    Press Keys Until quilt Is Highlighted           ${{ ['Down'] * 6 }}
    ${on_bottom}=           Is Highlighted Text     quilt
    Should Be True          ${on_bottom}
    Press Keys Until joker Is Highlighted           ${{ ['Up'] }}
    ${on_up}=               Is Highlighted Text     joker
    Should Be True          ${on_up}

Press Keys Until Target Is Highlighted Walks A Diagonal
    [Documentation]    Press Keys Until ${target} Is Highlighted presses the
    ...    given sequence of keys, so a repeated Down + Right walks the
    ...    highlight along the grid diagonal to the target.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until apple Is Highlighted
    Press Keys Until glide Is Highlighted           ${{ ['Down', 'Right'] * 4 }}
    ${on_target}=           Is Highlighted Text     glide
    Should Be True          ${on_target}

Enter Selects And Escape Clears The Selection
    [Documentation]    Enter turns the highlighted word green; Escape clears
    ...    every green selection.
    [Tags]                  yarf:certification_status: blocker
    Press Right Until wheat Is Highlighted
    Keys Combo              Return
    ${selected}=            Is Highlighted Text     wheat
    Should Be True          ${selected}
    Keys Combo              Left
    Keys Combo              Escape
    Sleep                   0.3
    ${cleared}=             Is Highlighted Text     wheat
    Should Not Be True      ${cleared}
    ${on_neighbour}=        Is Highlighted Text     vapor
    Should Be True          ${on_neighbour}

Close The Word Grid
    [Documentation]    Close the application.
    [Tags]                  yarf:certification_status: blocker
    Keys Combo              Alt_L                   F4


*** Keywords ***
Start Word Grid
    [Documentation]    Starts the word grid application and waits for it to be
    ...    open with the top-left word displayed.
    Start Process
    ...                     dbus-run-session
    ...                     --
    ...                     uv
    ...                     --project
    ...                     ${CURDIR}/grid
    ...                     run
    ...                     grid-app
    ...                     --contrast
    ...                     0.85
    Match Text              apple                   timeout=90
