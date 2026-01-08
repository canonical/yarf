*** Settings ***
Documentation       This suite tests Hid keyboard related keywords.

Resource            kvm.resource
Resource            wayland_trace.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::keyboard
...    yarf:test_group_id: com.canonical.yarf::hid


*** Test Cases ***
Test Keyword Type String Numbers
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Type String             123456

Assert Test Keyword Type String Numbers
    Assert Type String Events                       ${2,3,4,5,6,7}

Test Keyword Type String Alphabets
    Clear Trace File
    Type String             abcdef

Assert Test Keyword Type String Alphabets
    Assert Type String Events                       ${30,48,46,32,18,33}

Test Keyword Type String With Shift Key Symbols
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Type String             !@#$%^

Assert Test Keyword Type String With Shift Key Symbols
    Assert Type String Events                       ${2,3,4,5,6,7}          1

Test Keyword Type String With Shift Key Capital Letters
    Clear Trace File
    Type String             ABCDEF

Assert Test Keyword Type String With Shift Key Capital Letters
    Assert Type String Events                       ${30,48,46,32,18,33}    1

Test Keys Combo Numbers
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Keys Combo              1                       2                       3

Assert Test Keys Combo Numbers
    Assert Keys Combo Events                        ${2,3,4}

Test Keys Combo Alphabets
    Clear Trace File
    Keys Combo              Shift_L                 a                       b                       c

Assert Test Keys Combo Alphabets
    Assert Keys Combo Events                        ${42,30,48,46}

Test Keys Combo Function
    Clear Trace File
    Keys Combo              Control_L               Alt_L                   Delete

Assert Test Keys Combo Function
    Assert Keys Combo Events                        ${29,56,111}
