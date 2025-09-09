*** Settings ***
Documentation       This suite tests Hid pointer related keywords.

Resource            kvm.resource
Resource            wayland_trace.resource
Resource            Collections

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::pointer
...    yarf:test_group_id: com.canonical.yarf::hid


*** Test Cases ***
Test Button Actions
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Press LEFT Button
    Press MIDDLE Button
    Press RIGHT Button
    ${actions}=             Create Dictionary
    ...                     272=press
    ...                     274=press
    ...                     273=press
    Assert Pointer Button Events                    ${actions}

    Clear Trace File
    Release LEFT Button
    Release MIDDLE Button
    Release RIGHT Button
    ${actions}=             Create Dictionary
    ...                     272=release
    ...                     274=release
    ...                     273=release
    Assert Pointer Button Events                    ${actions}

    Clear Trace File
    Click LEFT Button
    Click MIDDLE Button
    Click RIGHT Button
    ${actions}=             Create Dictionary
    ...                     272=click
    ...                     274=click
    ...                     273=click
    Assert Pointer Button Events                    ${actions}

    Press LEFT Button
    Press RIGHT Button

    Clear Trace File
    Release Buttons
    ${actions}=             Create Dictionary
    ...                     272=release
    ...                     273=release
    Assert Pointer Button Events                    ${actions}

Test Keyword Move Pointer
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Hid.Move Pointer To Absolute                    100                     100
    Hid.Move Pointer To Proportional                0.1                     0.1
    Hid.Move Pointer To Proportional                1                       1
    Hid.Move Pointer To Absolute                    0                       0
    ${movements}=           Evaluate                [(100,100), (128,102), (1280,1024), (0,0)]
    Assert Pointer Movement Events                  ${movements}

Test Keyword Walk Pointer
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Hid.Walk Pointer To Absolute
    ...                     100
    ...                     100
    ...                     20
    ...                     0.01
    Hid.Walk Pointer To Proportional
    ...                     0.1
    ...                     0.1
    ...                     0.01
    ...                     0.01
    Hid.Walk Pointer To Proportional
    ...                     1
    ...                     1
    ...                     0.1
    ...                     0.01
    Hid.Walk Pointer To Absolute
    ...                     0
    ...                     0
    ...                     200
    ...                     0.01
    ${movements}=    Evaluate
    ...    [(100,100), (112,102), (125,102), (128,102), (256, 204), (384,307), (512, 409), (640,512), (768,614), (896,716), (1023,819), (1152,921), (1279,1023), (1280,1024), (0,0)]
    Assert Pointer Movement Events                  ${movements}
