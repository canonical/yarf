*** Settings ***
Documentation       Keyword definitions for specialised functionality
...                 for Keyboard, Mouse and Video-based manipulation.
...
...                 These keywords rely on VIDEO library to be initialized
...                 using the VIDEO.Init keyword. The initialization is
...                 platform-specific.

Library             Hid.py    AS    HID
Library             VideoInput.py    AS    VIDEO


*** Keywords ***
Press Key And Match
    [Arguments]    ${key}    ${template}    ${tentatives}=1    ${delay}=1
    ${combo}=    Create List    ${key}
    Press Combo And Match
    ...    ${combo}
    ...    ${template}
    ...    ${tentatives}
    ...    ${delay}

Press Combo And Match
    [Arguments]    ${keys-combo}    ${template}    ${tentatives}=1    ${delay}=1

    ${match}=    Set Variable    ${FALSE}
    FOR    ${index}    IN RANGE    ${tentatives}
        HID.Keys Combo    ${keys-combo}
        Sleep    ${delay}
        ${match}=    Run Keyword And Return Status
        ...    VIDEO.Match    ${template}    0.1
        IF    ${match}    BREAK
    END

    IF    ${match} == ${FALSE}    Fail    No match found

Press And Wait For Match
    [Arguments]    ${keys-combo}    ${template}    ${timeout}=10

    Keys Combo    ${keys-combo}
    VIDEO.Match    ${template}    ${timeout}

Get Center Of ${region}
    [Documentation]    Get the center point of a region.
    ...
    ...    Arguments:
    ...    - ${region}: Rectangular region represented by a dictionary
    ...    of integer values for "left", "right", "top", and "bottom" keys.
    ...
    ...    Return:
    ...    Center of the region, as a tuple (x, y) of integers.
    ${point}=    Evaluate
    ...    (int((${region}[left] + ${region}[right]) / 2), int((${region}[top] + ${region}[bottom]) / 2))
    RETURN    ${point}

Displace ${point} By (${x}, ${y})
    [Documentation]    Shift a point by the specified displacements along
    ...    the x and y axes.
    ...
    ...    Arguments:
    ...    - ${point}: Point to be displaced, as a tuple (x, y).
    ...    - ${x}: Displacement along the x-axis.
    ...    - ${y}: Displacement along the y-axis.
    ...
    ...    Return:
    ...    Displaced point, as a tuple (x, y) of integers.
    ${point}=    Evaluate    (int(${point}[0] + ${x}), int(${point}[1] + ${y}))
    RETURN    ${point}

Move Pointer To (${x}, ${y})
    [Documentation]    Move the pointer to an absolute position.
    ...
    ...    Arguments:
    ...    - ${x}: Integer absolute x-coordinate to move the pointer to.
    ...    - ${y}: Integer absolute y-coordinate to move the pointer to.
    HID.Move Pointer To Absolute    ${x}    ${y}

Move Pointer To ${destination}
    [Documentation]    Move the pointer to an absolute position or image
    ...    template.
    ...
    ...    Arguments:
    ...    - ${destination}: Where to move the pointer to. If ${destination}
    ...    is a tuple (x, y) of integers, the pointer will move to the
    ...    absolute position given by the tuple. Otherwise, if
    ...    ${destination} is the path of an image template file, the pointer
    ...    will move to the center of the first matching template region.
    ...
    ...    Return:
    ...    Absolute position of the pointer after the move, as a tuple (x, y)
    ...    of integers.
    IF    ${{isinstance($destination, str)}}
        ${regions}=    VIDEO.Match    ${destination}
        ${position}=    Get Center Of ${regions}[0]
    ELSE
        ${position}=    Set Variable    ${destination}
    END
    HID.Move Pointer To Absolute    ${position}[0]    ${position}[1]
    RETURN    ${position}

Move Pointer To Proportional (${x}, ${y})
    [Documentation]    Move the pointer to a destination position given as
    ...    proportions to the size of the display output.
    ...
    ...    Arguments:
    ...    - ${x}: Output-relative x-coordinate to move the pointer to.
    ...    It must be in the range 0..1, where 0 represents the left edge,
    ...    and 1 represents the right edge of the output.
    ...    - ${y}: Output-relative y-coordinate to move the pointer to.
    ...    It must be in the range 0..1, where 0 represents the top edge,
    ...    and 1 represents the bottom edge of the output.
    ...
    ...    Return:
    ...    Absolute position of the pointer after the move, as a tuple (x, y)
    ...    of integers.
    ${position}=    HID.Move Pointer To Proportional    ${x}    ${y}
    RETURN    ${position}

Walk Pointer To (${x}, ${y})
    [Documentation]    Move the pointer in incremental steps from the
    ...    current pointer position to an absolute position.
    ...
    ...    Arguments:
    ...    - ${x}: Integer absolute x-coordinate to walk the pointer to.
    ...    - ${y}: Integer absolute y-coordinate to walk the pointer to.
    ...    - ${step_distance} (optional): Size of each step, in pixels.
    ...    Default is 16.
    ...    - ${delay} (optional): Time to sleep after each step, in seconds.
    ...    Default is 0.01.
    [Arguments]    ${step_distance}=16    ${delay}=0.01
    HID.Walk Pointer To Absolute
    ...    ${x}
    ...    ${y}
    ...    ${step_distance}
    ...    ${delay}

Walk Pointer To ${destination}
    [Documentation]    Moves the pointer in incremental steps from the
    ...    current pointer position to an absolute position or image
    ...    template.
    ...
    ...    Arguments:
    ...    - ${destination}: Where to walk the pointer to. If ${destination}
    ...    is a tuple (x, y) of integers, the pointer will walk to the
    ...    absolute position given by the tuple. Otherwise, if
    ...    ${destination} is the path of an image template file, the pointer
    ...    will walk to the center of the first matching template region.
    ...    - ${step_distance} (optional): Size of each step, in pixels.
    ...    Default is 16.
    ...    - ${delay} (optional): Time to sleep after each step, in seconds.
    ...    Default is 0.01.
    ...
    ...    Return:
    ...    Absolute position of the pointer after the walk, as a tuple (x, y)
    ...    of integers.
    [Arguments]    ${step_distance}=16    ${delay}=0.01
    IF    ${{isinstance($destination, str)}}
        ${regions}=    VIDEO.Match    ${destination}
        ${position}=    Get Center Of ${regions}[0]
    ELSE
        ${position}=    Set Variable    ${destination}
    END
    HID.Walk Pointer To Absolute
    ...    ${position}[0]
    ...    ${position}[1]
    ...    ${step_distance}
    ...    ${delay}
    RETURN    ${position}

Walk Pointer To Proportional (${x}, ${y})
    [Documentation]    Move the pointer in incremental steps from the
    ...    current pointer position to a destination position given as
    ...    proportions to the size of the display output.
    ...
    ...    Arguments:
    ...    - ${x}: Output-relative x-coordinate to move the pointer to.
    ...    It must be in the range 0..1, where 0 represents the left edge,
    ...    and 1 represents the right edge of the output.
    ...    - ${y}: Output-relative y-coordinate to move the pointer to.
    ...    It must be in the range 0..1, where 0 represents the top edge,
    ...    and 1 represents the bottom edge of the output.
    ...    - ${step_distance} (optional): Size of each step, in pixels.
    ...    Default is 16.
    ...    - ${delay} (optional): Time to sleep after each step, in seconds.
    ...    Default is 0.01.
    ...
    ...    Return:
    ...    Absolute position of the pointer after the walk, as a tuple (x, y)
    ...    of integers.
    [Arguments]    ${step_distance}=16    ${delay}=0.01
    ${position}=    HID.Walk Pointer To Proportional
    ...    ${x}
    ...    ${y}
    ...    ${step_distance}
    ...    ${delay}
    RETURN    ${position}

Press ${button} Button
    [Documentation]    Press a button on the virtual pointer.
    ...
    ...    Arguments:
    ...    - ${button}: Button to press (LEFT|RIGHT|MIDDLE).
    HID.Press Pointer Button    ${button}

Release ${button} Button
    [Documentation]    Release a button on the virtual pointer.
    ...
    ...    Arguments:
    ...    - ${button}: Button to release (LEFT|RIGHT|MIDDLE).
    HID.Release Pointer Button    ${button}

Click ${button} Button
    [Documentation]    Click a button on the virtual pointer.
    ...
    ...    Arguments:
    ...    - ${button}: Button to click (LEFT|RIGHT|MIDDLE).
    HID.Click Pointer Button    ${button}

Release Buttons
    [Documentation]    Release all buttons on the virtual pointer.
    HID.Release Pointer Buttons
