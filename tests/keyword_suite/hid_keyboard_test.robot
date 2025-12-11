*** Settings ***
Documentation       This suite tests Hid keyboard related keywords.

Resource            kvm.resource
Resource            wayland_trace.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::keyboard
...    yarf:test_group_id: com.canonical.yarf::hid


*** Test Cases ***
Test Keyword Type String
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Type String             123456
    Assert Type String Events                       ${2,3,4,5,6,7}

    Clear Trace File
    Type String             abcdef
    Assert Type String Events                       ${30,48,46,32,18,33}

Test Keyword Type String With Shift Key
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Type String             !@#$%^
    Assert Type String Events                       ${2,3,4,5,6,7}          1

    Clear Trace File
    Type String             ABCDEF
    Assert Type String Events                       ${30,48,46,32,18,33}    1

Test Keys Combo
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Keys Combo              1                       2                       3
    Assert Keys Combo Events                        ${2,3,4}

    Clear Trace File
    Keys Combo              Shift_L                 a                       b                       c
    Assert Keys Combo Events                        ${42,30,48,46}

    Clear Trace File
    Keys Combo              Control_L               Alt_L                   Delete
    Assert Keys Combo Events                        ${29,56,111}
