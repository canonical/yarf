*** Settings ***
Documentation    Keyword definitions for handling Wayland trace.

Library          Collections
Library          OperatingSystem
Library          String


*** Variables ***
${WAYLAND_TRACE_PATH}       ~/wayland.trace


*** Keywords ***
Clear Trace File
    [Documentation]    Clear the current Wayland trace.
    Create File    ${WAYLAND_TRACE_PATH}    ${EMPTY}

Get Trace
    [Documentation]    Get the current Wayland trace as a list of lines.
    ${raw}=    Get File    ${WAYLAND_TRACE_PATH}
    # Remove any NUL bytes so splitting into lines works
    ${trace}=    Replace String Using Regexp
    ...    ${raw}
    ...    \\x00+
    ...    ${EMPTY}
    RETURN    ${trace.splitlines()}

Find Next Matching Line
    [Documentation]    Find the next line matching the pattern starting from index.
    [Arguments]    ${lines}    ${start}    ${pattern}
    ${n}=    Get Length    ${lines}
    FOR    ${i}    IN RANGE    ${start}    ${n}
        ${ok}=    Run Keyword And Return Status
        ...    Should Match Regexp    ${lines[${i}].strip()}    ${pattern}
        IF    ${ok}    RETURN    ${i}
    END
    Fail    Pattern not found from index ${start}: ${pattern}

Assert Type String Events
    [Documentation]    Assert key press events in the Wayland trace.
    ...    Verifies modifiers and key press/release events for each key.
    [Arguments]    ${key_ints}    ${modifier}=0

    ${trace}=    Get Trace
    ${n}=    Get Length    ${trace}
    VAR    ${idx}    0
    FOR    ${key_int}    IN    @{key_ints}
        VAR    ${modifier_before_press_pattern}
        ...    ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.modifiers\\(${modifier}, \\d+, \\d+, ${modifier}\\)$
        VAR    ${key_down_pattern}
        ...    ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_int}, 1\\)$
        VAR    ${key_up_pattern}
        ...    ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_int}, 0\\)$
        VAR    ${modifier_after_press_pattern}
        ...    ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.modifiers\\(0, \\d+, \\d+, 0\\)$
        VAR    ${sync_pattern}
        ...    ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$

        VAR    @{steps}
        ...    ${modifier_before_press_pattern}
        ...    ${key_down_pattern}
        ...    ${key_up_pattern}
        ...    ${modifier_after_press_pattern}
        ...    ${sync_pattern}
        FOR    ${step}    IN    @{steps}
            ${jdx}=    Find Next Matching Line
            ...    ${trace}
            ...    ${idx}
            ...    ${step}
            Should Be True    ${jdx} < ${n}
            ${idx}=    Evaluate    ${jdx} + 1
        END
        ${idx}=    Evaluate    ${idx} + 2
    END
    RETURN    ${idx}

Assert Keys Combo Events
    [Documentation]    Assert key combo events in the Wayland trace.
    ...    Verifies key down events for each key, then key up events in reverse order.
    [Arguments]    ${key_ints}

    ${trace}=    Get Trace
    ${n}=    Get Length    ${trace}
    VAR    ${down_start}    0
    VAR    ${up_start}    0
    ${n_keys}=    Get Length    ${key_ints}

    FOR    ${idx}    IN RANGE    ${n_keys}
        ${reverse_idx}=    Evaluate    ${n_keys} - ${idx} - 1
        VAR    ${key_down_pattern}
        ...    ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_ints[${idx}]}, 1\\)$
        VAR    ${key_up_pattern}
        ...    ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_ints[${reverse_idx}]}, 0\\)$

        VAR    &{steps}
        ...    ${down_start}=${key_down_pattern}
        ...    ${up_start}=${key_up_pattern}
        FOR    ${position}    ${pattern}    IN    &{steps}
            ${jdx}=    Find Next Matching Line
            ...    ${trace}
            ...    ${position}
            ...    ${pattern}
            Should Be True    ${jdx} < ${n}
            IF    ${{ $pattern == $key_down_pattern }}
                ${down_start}=    Evaluate    ${jdx} + 1
            ELSE
                ${up_start}=    Evaluate    ${jdx} + 1
            END
        END
    END

    VAR    ${sync_pattern}
    ...    ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$
    VAR    @{steps}    ${down_start}    ${up_start}
    FOR    ${position}    IN    @{steps}
        ${jdx}=    Find Next Matching Line
        ...    ${trace}
        ...    ${position}
        ...    ${sync_pattern}
        Should Be True    ${jdx} < ${n}
    END

Assert Pointer Button Events
    [Documentation]    Assert pointer button events in the Wayland trace.
    ...    Verifies button press, release, and click events with frame and sync.
    [Arguments]    ${actions}

    ${trace}=    Get Trace
    ${n}=    Get Length    ${trace}
    VAR    ${idx}    0

    FOR    ${button_int}    ${action}    IN    &{actions}
        VAR    ${button_down_pattern}
        ...    ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.button\\(\\d+, ${button_int}, 1\\)$
        VAR    ${button_up_pattern}
        ...    ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.button\\(\\d+, ${button_int}, 0\\)$
        VAR    ${frame_pattern}    ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.frame\\(\\)$
        VAR    ${sync_pattern}
        ...    ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$
        IF    '${action}' == 'press'
            VAR    @{steps}
            ...    ${button_down_pattern}
            ...    ${frame_pattern}
            ...    ${sync_pattern}
        ELSE IF    '${action}' == 'release'
            VAR    @{steps}
            ...    ${button_up_pattern}
            ...    ${frame_pattern}
            ...    ${sync_pattern}
        ELSE IF    '${action}' == 'click'
            VAR    @{steps}
            ...    ${button_down_pattern}
            ...    ${frame_pattern}
            ...    ${sync_pattern}
            ...    ${button_up_pattern}
            ...    ${frame_pattern}
            ...    ${sync_pattern}
        END
        FOR    ${step}    IN    @{steps}
            ${jdx}=    Find Next Matching Line
            ...    ${trace}
            ...    ${idx}
            ...    ${step}
            Should Be True    ${jdx} < ${n}
            ${idx}=    Evaluate    ${jdx} + 1
            IF    ${{ $step == $sync_pattern }}
                ${idx}=    Evaluate    ${idx} + 2
            END
        END
    END
    RETURN    ${idx}

Assert Pointer Movement Events
    [Documentation]    Assert pointer movement events in the Wayland trace.
    ...    Verifies motion_absolute, frame, and sync events for each movement.
    [Arguments]    ${movements}

    ${trace}=    Get Trace
    ${n}=    Get Length    ${trace}
    VAR    ${idx}    0

    FOR    ${movement}    IN    @{movements}
        ${x}    ${y}=    Evaluate    $movement
        VAR    ${motion_pattern}
        ...    ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.motion_absolute\\(\\d+, ${x}, ${y}, \\d+, \\d+\\)$
        VAR    ${frame_pattern}    ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.frame\\(\\)$
        VAR    ${sync_pattern}
        ...    ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$
        VAR    @{steps}
        ...    ${motion_pattern}
        ...    ${frame_pattern}
        ...    ${sync_pattern}
        FOR    ${step}    IN    @{steps}
            ${jdx}=    Find Next Matching Line
            ...    ${trace}
            ...    ${idx}
            ...    ${step}
            Should Be True    ${jdx} < ${n}
            ${idx}=    Evaluate    ${jdx} + 1
            IF    ${{ $step == $sync_pattern }}
                ${idx}=    Evaluate    ${idx} + 2
            END
        END
    END
    RETURN    ${idx}
