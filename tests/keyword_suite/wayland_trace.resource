*** Settings ***
Documentation       Keyword definitions for handling Wayland trace.

Library             OperatingSystem
Library             Collections
Library             String


*** Variables ***
${WAYLAND_TRACE_PATH}       ~/wayland.trace


*** Keywords ***
Clear Trace File
    [Documentation]    Clear the current Wayland trace.
    Create File             ${WAYLAND_TRACE_PATH}                           ${EMPTY}

Get Trace
    [Documentation]    Get the current Wayland trace as a list of lines.
    ${raw}=                 Get File                ${WAYLAND_TRACE_PATH}
    # Remove any NUL bytes so splitting into lines works
    ${trace}=               Replace String Using Regexp
    ...                     ${raw}
    ...                     \\x00+
    ...                     ${EMPTY}
    RETURN                  ${trace.splitlines()}

Find Next Matching Line
    [Arguments]             ${lines}                ${start}                ${pattern}
    ${n}=                   Get Length              ${lines}
    FOR    ${i}    IN RANGE    ${start}    ${n}
        ${ok}=                  Run Keyword And Return Status
        ...                     Should Match Regexp     ${lines[${i}].strip()}                          ${pattern}
        IF    ${ok}    RETURN    ${i}
    END
    Fail                    Pattern not found from index ${start}: ${pattern}

Assert Type String Events
    [Documentation]    This function asserts that the following calls are present in the Wayland trace for every key:
    ...    zwp_virtual_keyboard_v1[#@]*.modifiers(${modifier}, 0, 0, ${modifier})
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int}, 1)
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int}, 0)
    ...    zwp_virtual_keyboard_v1[#@]*.modifiers(0, 0, 0, 0)
    ...    wl_display*.sync(new id wl_callback*)
    [Arguments]             ${key_ints}             ${modifier}=0

    ${trace}=               Get Trace
    ${n}=                   Get Length              ${trace}
    ${idx}=                 Set Variable            0
    FOR    ${key_int}    IN    @{key_ints}
        ${modifier_before_press_pattern}=    Set Variable
        ...    ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.modifiers\\(${modifier}, \\d+, \\d+, ${modifier}\\)$
        ${key_down_pattern}=    Set Variable
        ...                     ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_int}, 1\\)$
        ${key_up_pattern}=      Set Variable
        ...                     ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_int}, 0\\)$
        ${modifier_after_press_pattern}=                Set Variable
        ...                     ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.modifiers\\(0, \\d+, \\d+, 0\\)$
        ${sync_pattern}=        Set Variable            ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$

        FOR    ${step}    IN    ${modifier_before_press_pattern}    ${key_down_pattern}    ${key_up_pattern}    ${modifier_after_press_pattern}    ${sync_pattern}
            ${jdx}=                 Find Next Matching Line
            ...                     ${trace}
            ...                     ${idx}
            ...                     ${step}
            Should Be True          ${jdx} < ${n}
            ${idx}=                 Evaluate                ${jdx} + 1
        END
        ${idx}=                 Evaluate                ${idx} + 2
    END
    RETURN                  ${idx}

Assert Keys Combo Events
    [Documentation]    This function asserts that the following calls are present in the Wayland trace for every key in the combo:
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int_1}, 1)
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int_2}, 1)
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int_3}, 1)
    ...    wl_display[#@]*.sync(new id wl_callback[#@]*)
    ...    ...
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int_3}, 0)
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int_2}, 0)
    ...    zwp_virtual_keyboard_v1[#@]*.key(*, ${key_int_1}, 0)
    ...    wl_display[#@]*.sync(new id wl_callback[#@]*)
    [Arguments]             ${key_ints}

    ${trace}=               Get Trace
    ${n}=                   Get Length              ${trace}
    ${down_start}=          Set Variable            0
    ${up_start}=            Set Variable            0
    ${n_keys}=              Get Length              ${key_ints}

    FOR    ${idx}    IN RANGE    ${n_keys}
        ${reverse_idx}=         Evaluate                ${n_keys} - ${idx} - 1
        ${key_down_pattern}=    Set Variable
        ...                     ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_ints[${idx}]}, 1\\)$
        ${key_up_pattern}=      Set Variable
        ...                     ^.*zwp_virtual_keyboard_v1[#@]\\d+\\.key\\(\\d+, ${key_ints[${reverse_idx}]}, 0\\)$

        ${steps}=               Create Dictionary
        ...                     ${down_start}=${key_down_pattern}
        ...                     ${up_start}=${key_up_pattern}
        FOR    ${position}    ${pattern}    IN    &{steps}
            ${jdx}=                 Find Next Matching Line
            ...                     ${trace}
            ...                     ${position}
            ...                     ${pattern}
            Should Be True          ${jdx} < ${n}
            IF    ${{ $pattern == $key_down_pattern }}
                ${down_start}=          Evaluate                ${jdx} + 1
            ELSE
                ${up_start}=            Evaluate                ${jdx} + 1
            END
        END
    END

    ${sync_pattern}=        Set Variable            ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$
    ${steps}=               Create List
    ...                     ${down_start}
    ...                     ${up_start}
    FOR    ${position}    IN    @{steps}
        ${jdx}=                 Find Next Matching Line
        ...                     ${trace}
        ...                     ${position}
        ...                     ${sync_pattern}
        Should Be True          ${jdx} < ${n}
    END

Assert Pointer Button Events
    [Documentation]    This function asserts that the following calls are present
    ...    in the Wayland trace for every button:
    ...    Press:
    ...    zwlr_virtual_pointer_v1[#@]*.button(*, ${button_int}, 1)
    ...    Release:
    ...    zwlr_virtual_pointer_v1[#@]*.button(*, ${button_int}, 0)
    ...    And for either Press or Release:
    ...    zwlr_virtual_pointer_v1[#@]*.frame()
    ...    wl_display[#@]*.sync(new id wl_callback[#@]*)
    [Arguments]             ${actions}

    ${trace}=               Get Trace
    ${n}=                   Get Length              ${trace}
    ${idx}=                 Set Variable            0

    FOR    ${button_int}    ${action}    IN    &{actions}
        ${button_down_pattern}=                         Set Variable
        ...                     ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.button\\(\\d+, ${button_int}, 1\\)$
        ${button_up_pattern}=                           Set Variable
        ...                     ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.button\\(\\d+, ${button_int}, 0\\)$
        ${frame_pattern}=       Set Variable            ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.frame\\(\\)$
        ${sync_pattern}=        Set Variable            ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$
        IF    '${action}' == 'press'
            ${steps}=               Create List
            ...                     ${button_down_pattern}
            ...                     ${frame_pattern}
            ...                     ${sync_pattern}
        ELSE IF    '${action}' == 'release'
            ${steps}=               Create List
            ...                     ${button_up_pattern}
            ...                     ${frame_pattern}
            ...                     ${sync_pattern}
        ELSE IF    '${action}' == 'click'
            ${steps}=               Create List
            ...                     ${button_down_pattern}
            ...                     ${frame_pattern}
            ...                     ${sync_pattern}
            ...                     ${button_up_pattern}
            ...                     ${frame_pattern}
            ...                     ${sync_pattern}
        END
        FOR    ${step}    IN    @{steps}
            ${jdx}=                 Find Next Matching Line
            ...                     ${trace}
            ...                     ${idx}
            ...                     ${step}
            Should Be True          ${jdx} < ${n}
            ${idx}=                 Evaluate                ${jdx} + 1
            IF    ${{ $step == $sync_pattern }}
                ${idx}=                 Evaluate                ${idx} + 2
            END
        END
    END
    RETURN                  ${idx}

Assert Pointer Movement Events
    [Documentation]    This function asserts that the following calls are present in the Wayland trace for a pointer move:
    ...    zwlr_virtual_pointer_v1[#@]*.motion_absolute(*, ${x}, ${y}, *, *)
    ...    zwlr_virtual_pointer_v1[#@]*.frame()
    ...    wl_display[#@]*.sync(new id wl_callback[#@]*)
    [Arguments]             ${movements}

    ${trace}=               Get Trace
    ${n}=                   Get Length              ${trace}
    ${idx}=                 Set Variable            0

    FOR    ${movement}    IN    @{movements}
        ${x}                    ${y}=                   Evaluate                $movement
        ${motion_pattern}=      Set Variable
        ...                     ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.motion_absolute\\(\\d+, ${x}, ${y}, \\d+, \\d+\\)$
        ${frame_pattern}=       Set Variable            ^.*zwlr_virtual_pointer_v1[#@]\\d+\\.frame\\(\\)$
        ${sync_pattern}=        Set Variable            ^.*wl_display[#@]\\d+\\.sync\\(new id wl_callback[#@]\\d+\\)$
        ${steps}=               Create List
        ...                     ${motion_pattern}
        ...                     ${frame_pattern}
        ...                     ${sync_pattern}
        FOR    ${step}    IN    @{steps}
            ${jdx}=                 Find Next Matching Line
            ...                     ${trace}
            ...                     ${idx}
            ...                     ${step}
            Should Be True          ${jdx} < ${n}
            ${idx}=                 Evaluate                ${jdx} + 1
            IF    ${{ $step == $sync_pattern }}
                ${idx}=                 Evaluate                ${idx} + 2
            END
        END
    END
    RETURN                  ${idx}
