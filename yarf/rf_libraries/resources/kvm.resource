*** Settings ***
Documentation       Keyword definitions for specialised functionality
...                 for Keyboard, Mouse and Video-based manipulation.
...
...                 These keywords rely on VideoInput and Hid libraries
...                 to be initialized using the Init keyword.
...                 The initialization is platform-specific.

Library             Collections
Library             Hid.py
Library             VideoInput.py
Variables           video_input_vars.py


*** Keywords ***
Press Key And Match
    [Documentation]    If the provided template is not already matching, press a key until it does.
    [Arguments]             ${key}                  ${template}             ${tentatives}=1         ${timeout}=2
    ${combo}=               Create List             ${key}
    Press Combo And Match
    ...                     ${combo}
    ...                     ${template}
    ...                     ${tentatives}
    ...                     ${timeout}

Press Combo And Match
    [Documentation]    If the provided template is not already matching, press a key combination until it does.
    [Arguments]
    ...                     ${keys-combo}
    ...                     ${template}
    ...                     ${tentatives}=1
    ...                     ${timeout}=2
    ...                     ${tolerance}=${DEFAULT_TEMPLATE_MATCHING_TOLERANCE}

    ${match}=               Run Keyword And Return Status
    ...                     Match                   ${template}             ${timeout}              ${tolerance}
    IF    ${match}
        Log                     Template is already matching.                   html=true               console=true
        RETURN
    END

    FOR    ${index}    IN RANGE    ${tentatives}
        Hid.Keys Combo          ${keys-combo}
        ${match}=               Run Keyword And Return Status
        ...                     Match                   ${template}             ${timeout}              ${tolerance}
        IF    ${match}    BREAK
    END

    IF    ${match} == ${FALSE}    Fail    No match found

Press And Wait For Match
    [Arguments]
    ...                     ${keys-combo}
    ...                     ${template}
    ...                     ${timeout}=10
    ...                     ${tolerance}=${DEFAULT_TEMPLATE_MATCHING_TOLERANCE}

    Keys Combo              ${keys-combo}
    Match                   ${template}             ${timeout}              ${tolerance}

Get Center Of ${region}
    [Documentation]    Get the center point of a region.
    ...
    ...    Embedded arguments:
    ...    - ${region}: Rectangular region represented by a dictionary
    ...    of integer values for "left", "right", "top", and "bottom" keys.
    ...
    ...    Return:
    ...    Center of the region, as a tuple (x, y) of integers.
    ${point}=    Evaluate
    ...    (int((${region}[left] + ${region}[right]) / 2), int((${region}[top] + ${region}[bottom]) / 2))
    RETURN                  ${point}

Displace ${point} By (${x}, ${y})
    [Documentation]    Shift a point by the specified displacements along
    ...    the x and y axes.
    ...
    ...    Embedded arguments:
    ...    - ${point}: Point to be displaced, as a tuple (x, y).
    ...    - ${x}: Displacement along the x-axis.
    ...    - ${y}: Displacement along the y-axis.
    ...
    ...    Return:
    ...    Displaced point, as a tuple (x, y) of integers.
    ${point}=               Evaluate                (int(${point}[0] + ${x}), int(${point}[1] + ${y}))
    RETURN                  ${point}

Get Position Of ${target}
    [Documentation]    Get a position from an absolute coordinate, image
    ...    template, or string.
    ...
    ...    Embedded arguments:
    ...    - ${target}: If ${target} is a tuple (x, y) of integers,
    ...    the position will be the absolute position given by the tuple.
    ...    Otherwise, if ${target} is the path of an image template file,
    ...    the position will be the center of the first matching template region.
    ...    ${target} can also be a string, and the position will be the
    ...    center of the found text.
    ...
    ...    Return:
    ...    Absolute position as a tuple (x, y) of integers.
    IF    ${{ isinstance($target, tuple) }}
        ${position}=            Set Variable            ${target}
    ELSE IF    ${{ isinstance($target, str) }}
        IF    ${{ os.path.exists($target) }}
            ${regions}=             Match                   ${target}
            ${position}=            Get Center Of ${regions}[0]
        ELSE
            Log
            ...                     Assuming ${target} is a string as it isn't a file which exists.
            ...                     html=true
            ...                     console=true
            ${position}=            Get Text Position       text=${target}
        END
    ELSE
        Fail                    Unsupported target type
    END
    RETURN                  ${position}

Move Pointer To (${x}, ${y})
    [Documentation]    Move the pointer to an absolute position.
    ...
    ...    Embedded arguments:
    ...    - ${x}: Integer absolute x-coordinate to move the pointer to.
    ...    - ${y}: Integer absolute y-coordinate to move the pointer to.
    Hid.Move Pointer To Absolute                    ${x}                    ${y}

Move Pointer To ${destination}
    [Documentation]    Move the pointer to an absolute position or image
    ...    template.
    ...
    ...    Embedded arguments:
    ...    - ${destination}: Where to move the pointer to. If ${destination}
    ...    is a tuple (x, y) of integers, the pointer will move to the
    ...    absolute position given by the tuple. Otherwise, if
    ...    ${destination} is the path of an image template file, the pointer
    ...    will move to the center of the first matching template region.
    ...    ${destination} can also be a string, and the pointer will move to the
    ...    center of the found text.
    ...
    ...    Return:
    ...    Absolute position of the pointer after the move, as a tuple (x, y)
    ...    of integers.
    ${position}=            Get Position Of ${destination}
    Hid.Move Pointer To Absolute                    ${position}[0]          ${position}[1]
    RETURN                  ${position}

Move Pointer To ${destination} In ${domain}
    [Documentation]    Move the pointer to an absolute position or image
    ...    template.
    ...
    ...    Embedded arguments:
    ...    - ${destination}: Where to move the pointer to. If ${destination}
    ...    is a tuple (x, y) of integers, the pointer will move to the
    ...    absolute position given by the tuple. Otherwise, if
    ...    ${destination} is the path of an image template file, the pointer
    ...    will move to the center of the first matching template region.
    ...    ${destination} can also be a string, and the pointer will move to the
    ...    center of the found text.
    ...
    ...    - ${domain}: Given region or template to search for ${destination} within.
    ...
    ...    Return:
    ...    Absolute position of the pointer after the move, as a tuple (x, y)
    ...    of integers.
    IF    ${{ isinstance($domain, dict) }}
        ${target_region}=       Set Variable            ${domain}
    ELSE IF    ${{ isinstance($domain, str) }}
        IF    ${{ os.path.exists($domain) }}
            ${sub_regions}=         Match                   ${domain}
            ${target_region}=       Set Variable            ${sub_regions}[0]
            Remove From Dictionary                          ${target_region}        path
        ELSE
            Fail                    Template ${domain} doesn't exist!
        END
    ELSE
        Fail                    Incorrect domain type
    END

    IF    ${{ os.path.exists($destination) }}
        ${regions}=             Match
        ...                     template=${destination}
        ...                     region=${target_region}
        ${position}=            Get Center Of ${regions}[0]
    ELSE
        ${position}=            Get Text Position
        ...                     text=${destination}
        ...                     region=${target_region}
    END

    Hid.Move Pointer To Absolute                    ${position}[0]          ${position}[1]
    RETURN                  ${position}

Move Pointer To Proportional (${x}, ${y})
    [Documentation]    Move the pointer to a destination position given as
    ...    proportions to the size of the display output.
    ...
    ...    Embedded arguments:
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
    ${position}=            Hid.Move Pointer To Proportional                ${x}                    ${y}
    RETURN                  ${position}

Walk Pointer To (${x}, ${y})
    [Documentation]    Move the pointer in incremental steps from the
    ...    current pointer position to an absolute position.
    ...
    ...    Embedded arguments:
    ...    - ${x}: Integer absolute x-coordinate to walk the pointer to.
    ...    - ${y}: Integer absolute y-coordinate to walk the pointer to.
    ...    - ${step_distance} (optional): Size of each step, in pixels.
    ...    Default is 16.
    ...    - ${delay} (optional): Time to sleep after each step, in seconds.
    ...    Default is 0.01.
    [Arguments]             ${step_distance}=16     ${delay}=0.01
    Hid.Walk Pointer To Absolute
    ...                     ${x}
    ...                     ${y}
    ...                     ${step_distance}
    ...                     ${delay}

Walk Pointer To ${destination}
    [Documentation]    Moves the pointer in incremental steps from the
    ...    current pointer position to an absolute position or image
    ...    template.
    ...
    ...    Embedded arguments:
    ...    - ${destination}: Where to walk the pointer to. If ${destination}
    ...    is a tuple (x, y) of integers, the pointer will walk to the
    ...    absolute position given by the tuple. Otherwise, if
    ...    ${destination} is the path of an image template file, the pointer
    ...    will walk to the center of the first matching template region.
    ...    ${destination} can also be a string, and the pointer will move to the
    ...    center of the found text.
    ...    - ${step_distance} (optional): Size of each step, in pixels.
    ...    Default is 16.
    ...    - ${delay} (optional): Time to sleep after each step, in seconds.
    ...    Default is 0.01.
    ...
    ...    Return:
    ...    Absolute position of the pointer after the walk, as a tuple (x, y)
    ...    of integers.
    [Arguments]             ${step_distance}=16     ${delay}=0.01
    ${position}=            Get Position Of ${destination}
    Hid.Walk Pointer To Absolute
    ...                     ${position}[0]
    ...                     ${position}[1]
    ...                     ${step_distance}
    ...                     ${delay}
    RETURN                  ${position}

Walk Pointer To Proportional (${x}, ${y})
    [Documentation]    Move the pointer in incremental steps from the
    ...    current pointer position to a destination position given as
    ...    proportions to the size of the display output.
    ...
    ...    Embedded arguments:
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
    [Arguments]             ${step_distance}=0.01                           ${delay}=0.01
    ${position}=            Hid.Walk Pointer To Proportional
    ...                     ${x}
    ...                     ${y}
    ...                     ${step_distance}
    ...                     ${delay}
    RETURN                  ${position}

Press ${button} Button
    [Documentation]    Press a button on the virtual pointer.
    ...
    ...    Embedded arguments:
    ...    - ${button}: Button to press (LEFT|RIGHT|MIDDLE).
    Hid.Press Pointer Button                        ${button}

Release ${button} Button
    [Documentation]    Release a button on the virtual pointer.
    ...
    ...    Embedded arguments:
    ...    - ${button}: Button to release (LEFT|RIGHT|MIDDLE).
    Hid.Release Pointer Button                      ${button}

Click ${button} Button
    [Documentation]    Click a button on the virtual pointer.
    ...
    ...    Embedded arguments:
    ...    - ${button}: Button to click (LEFT|RIGHT|MIDDLE).
    Hid.Click Pointer Button                        ${button}

Click ${button} Button On ${destination}
    [Documentation]    Move the virtual pointer to the destination and click the button.
    ...
    ...    See `Move Pointer to ${destination}` for details.
    ...
    ...    Embedded arguments:
    ...    - ${button}: Button to click (LEFT|RIGHT|MIDDLE).
    ...    - ${destination}: The template or location to click on.
    Move Pointer To ${destination}
    Click ${button} Button

Release Buttons
    [Documentation]    Release all buttons on the virtual pointer.
    Hid.Release Pointer Buttons

Ensure ${destination} Does Not Match
    [Documentation]    Ensure a given template or string doesn't match within a given timeout and
    ...    number of attempts.
    ...    This function is intended to be used like:
    ...    "This given template or image should, by the end of this time,
    ...    not be found on the screen."
    ...
    ...    Embedded arguments:
    ...    - ${destination}: The template or string to match.
    ...    This function ensures that the given destination is not found.
    [Arguments]             ${timeout}=2

    IF    ${{ os.path.exists($destination) }}
        ${match}=               Run Keyword And Return Status
        ...                     Match                   ${destination}          timeout=${timeout}
    ELSE
        Log
        ...                     Assuming ${destination} is a string as it isn't a file which exists.
        ...                     html=true
        ...                     console=true
        ${match}=               Run Keyword And Return Status
        ...                     Match Text              ${destination}          timeout=${timeout}
    END
    IF    ${match}
        Fail                    Found ${destination} where it wasn't intended or expected
    END

Drag And Drop On ${destination}
    [Documentation]    Drag and drop the current target (where the pointer is) on a destination.
    ...
    ...    Embedded arguments:
    ...    - ${destination}: Can be a string, or the path of an image template file representing
    ...    the target location to drop on, or a coordinate tuple (x, y) of integers representing the
    ...    absolute position to drop on. For details please see `Walk Pointer To ${destination}`.
    ...
    [Arguments]             ${step_distance}=16     ${delay}=0.01

    Press LEFT Button
    ${end_position}=        Walk Pointer To ${destination}                  ${step_distance}        ${delay}
    Release LEFT Button
    RETURN                  ${end_position}
