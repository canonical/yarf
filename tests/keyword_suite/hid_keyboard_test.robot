*** Settings ***
Documentation    Test suite for HID keyboard related keywords.

Resource         kvm.resource
Resource         wayland_trace.resource

Test Tags
...    robot:stop-on-failure
...    yarf:category_id:com.canonical.yarf::keyboard
...    yarf:test_group_id:com.canonical.yarf::hid
...    yarf:certification_status:blocker


*** Test Cases ***
Test Keyword Type String Numbers
    [Documentation]    Test typing numeric strings.
    Clear Trace File
    Type String    123456

Assert Test Keyword Type String Numbers
    [Documentation]    Verify number key events in trace.
    Assert Type String Events    ${2,3,4,5,6,7}

Test Keyword Type String Alphabets
    [Documentation]    Test typing alphabetic strings.
    Clear Trace File
    Type String    abcdef

Assert Test Keyword Type String Alphabets
    [Documentation]    Verify alphabet key events in trace.
    Assert Type String Events    ${30,48,46,32,18,33}

Test Keyword Type String With Shift Key Symbols
    [Documentation]    Test typing symbols that require shift key.
    Clear Trace File
    Type String    !@#$%^

Assert Test Keyword Type String With Shift Key Symbols
    [Documentation]    Verify shift+key events for symbols in trace.
    Assert Type String Events    ${2,3,4,5,6,7}    1

Test Keyword Type String With Shift Key Capital Letters
    [Documentation]    Test typing capital letters.
    Clear Trace File
    Type String    ABCDEF

Assert Test Keyword Type String With Shift Key Capital Letters
    [Documentation]    Verify shift+key events for capitals in trace.
    Assert Type String Events    ${30,48,46,32,18,33}    1

Test Keys Combo Numbers
    [Documentation]    Test key combinations with numbers.
    Clear Trace File
    Keys Combo    1    2    3

Assert Test Keys Combo Numbers
    [Documentation]    Verify key combo events for numbers in trace.
    Assert Keys Combo Events    ${2,3,4}

Test Keys Combo Alphabets
    [Documentation]    Test key combinations with alphabets.
    Clear Trace File
    Keys Combo    Shift_L    a    b    c

Assert Test Keys Combo Alphabets
    [Documentation]    Verify key combo events for alphabets in trace.
    Assert Keys Combo Events    ${42,30,48,46}

Test Keys Combo Function
    [Documentation]    Test key combinations with function keys.
    Clear Trace File
    Keys Combo    Control_L    Alt_L    Delete

Assert Test Keys Combo Function
    [Documentation]    Verify key combo events for function keys in trace.
    Assert Keys Combo Events    ${29,56,111}
