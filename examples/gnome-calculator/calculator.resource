*** Settings ***
Documentation       Keywords to launch, drive and check GNOME Calculator.
...
...                 The calculator is driven with the keyboard, using the
...                 shortcuts defined in its source (gnome-calculator.vala),
...                 and checked by reading the screen with OCR.
...
...                 The result is shown in the "entry", the line above the
...                 buttons, but it also stays in the history and some buttons
...                 are labelled with digits. So checks never search the whole
...                 screen: they read a box placed relative to the "mod"
...                 button, which doesn't move relative to the entry, even if
...                 the window is moved or resized.
...
...                 The checks compare whole lines of text. Searching with
...                 `Match Text` is not enough to check a value: it accepts
...                 similar text and part of a line, so "12" would match "120"
...                 and 0.666666666 would match 0.666666667.

Resource            kvm.resource


*** Variables ***
# Boxes as "left,top,right,bottom" offsets in pixels from the centre of the
# "mod" button. They stay inside the window, and are about 340 pixels wide:
# the OCR doesn't read text in a much wider crop.
${MODE}             Basic
&{BASIC}            entry=-240,-98,104,-33              history=-240,-216,104,-100
&{ADVANCED}         entry=-222,-179,100,-114            history=-222,-297,100,-181
&{SHORTCUTS}        Basic=b                             Advanced=a


*** Keywords ***
Launch Calculator
    [Documentation]    Open GNOME Calculator from the Activities overview, in
    ...    Basic mode.
    ...
    ...    Super opens the overview when it is closed and closes it when it
    ...    is open. So close it first (Escape clears the search, then closes
    ...    the overview), and check that it is open before typing: otherwise
    ...    the keys would go to the desktop.
    Keys Combo              Escape
    Keys Combo              Escape
    Sleep                   1s
    Keys Combo              Super_L
    Match Text              regex:search            timeout=10
    Sleep                   1s
    Type String             calculator
    Sleep                   2s
    Keys Combo              Return
    Match Text              Undo                    timeout=30
    Switch To Basic Mode

Close Calculator
    [Documentation]    Quit the calculator, and wait until its window is gone.
    ...    It remembers its mode, so go back to Basic first.
    Switch To Basic Mode
    Keys Combo              Control_L               q
    Wait Until Keyword Succeeds                     15s                     1s
    ...                     Run Keyword And Expect Error                    *Timed out looking for*
    ...                     Match Text              Undo                    timeout=1

Switch To ${mode} Mode
    [Documentation]    Switch mode with its keyboard shortcut, and check that
    ...    the title shows it.
    Keys Combo              Control_L               Alt_L                   ${SHORTCUTS}[${mode}]
    Match Text              ${mode}                 timeout=10
    Set Suite Variable      ${MODE}                 ${mode}

Calculate ${expression}
    [Documentation]    Clear the entry, type an expression and solve it.
    Clear Entry
    Enter ${expression}

Clear Entry
    [Documentation]    Escape clears the entry. If the completion list is
    ...    open it only closes it, so press it twice.
    Keys Combo              Escape
    Keys Combo              Escape

Enter ${expression}
    [Documentation]    Type an expression and solve it, keeping what is already
    ...    in the entry, such as the previous answer.
    Type String             ${expression}
    Keys Combo              Return

Get Box ${area}
    [Documentation]    Get the [left, top, right, bottom] pixels of the entry or
    ...    of the history, for the current mode.
    ${x}                    ${y}=                   Get Text Position       mod
    ${offsets}=             Set Variable If         '${MODE}' == 'Basic'
    ...                     ${BASIC}[${area}]       ${ADVANCED}[${area}]
    ${box}=                 Evaluate
    ...                     [int(o) + a for o, a in zip($offsets.split(","), ($x, $y, $x, $y))]
    RETURN                  ${box}

Get Lines Of ${area}
    [Documentation]    Read the entry or the history with OCR, as a list of
    ...    lines without the text cursor.
    ${box}=                 Get Box ${area}
    ${screen}=              Grab Screenshot
    ${crop}=                Evaluate                $screen.crop(tuple($box))
    ${text}=                Read Text               ${crop}
    ${lines}=               Evaluate
    ...                     [l for l in (line.strip().strip("|").strip() for line in $text.splitlines()) if l]
    RETURN                  ${lines}

Area Should Contain
    [Documentation]    A line of the entry or of the history is exactly a text.
    ...    It is not a search for something similar, so "12" is not "120".
    [Arguments]             ${area}                 ${text}
    ${lines}=               Get Lines Of ${area}
    Should Contain          ${lines}                ${text}
    ...                     msg=The ${area} shows ${lines}, not '${text}'.
    ...                     values=${FALSE}

Area Should Not Contain
    [Documentation]    No line of the entry or of the history is a text. Before
    ...    using it, check that the text was there, because it also passes if
    ...    the OCR reads nothing.
    [Arguments]             ${area}                 ${text}
    ${lines}=               Get Lines Of ${area}
    Should Not Contain      ${lines}                ${text}
    ...                     msg=The ${area} still shows '${text}'.
    ...                     values=${FALSE}

Entry Should Show ${text}
    [Documentation]    The entry, where the result and the errors are shown,
    ...    shows a line with exactly this text. It waits for the screen to
    ...    update.
    Wait Until Keyword Succeeds                     5s                      500ms
    ...                     Area Should Contain     entry                   ${text}

Entry Should Not Show ${text}
    [Documentation]    The entry doesn't show a line with this text.
    Wait Until Keyword Succeeds                     5s                      500ms
    ...                     Area Should Not Contain                         entry                   ${text}

History Should Show ${text}
    [Documentation]    The history shows a line with exactly this text.
    Wait Until Keyword Succeeds                     5s                      500ms
    ...                     Area Should Contain     history                 ${text}

History Should Not Show ${text}
    [Documentation]    The history doesn't show a line with this text.
    Wait Until Keyword Succeeds                     5s                      500ms
    ...                     Area Should Not Contain                         history                 ${text}
