*** Settings ***
Documentation       This suite tests Hid pointer related keywords.

Resource            kvm.resource
Resource            wayland_trace.resource

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
    Move Pointer To (100, 100)
    Move Pointer To Proportional (0.1, 0.1)
    Move Pointer To Proportional (1, 1)
    Move Pointer To (0, 0)
    ${movements}=           Evaluate                [(100,100), (128,102), (1280,1024), (0,0)]
    Assert Pointer Movement Events                  ${movements}

Test Keyword Walk Pointer
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Walk Pointer To (100, 100)
    ...                     20
    ...                     0.01
    Walk Pointer To Proportional (0, 0)
    ...                     0.01
    ...                     0.01

    ${movements}=    Evaluate
    ...    [(22, 17), (44, 35) ,(67, 53), (89, 71), (100, 89), (100, 100), (87, 89), (74, 79), (61, 69), (48, 59), (36, 48), (23, 38), (10, 28), (0, 18), (0, 7), (0, 0)]
    Assert Pointer Movement Events                  ${movements}

Test Keyword Click Button On Destination
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Click LEFT Button On ${100,_100}
    ${movements}=           Evaluate                [(100, 100)]
    Assert Pointer Movement Events                  ${movements}

    ${actions}=             Create Dictionary
    ...                     272=click
    Assert Pointer Button Events                    ${actions}

Test Keyword Drag And Drop On Destination
    [Tags]                  yarf:certification_status: blocker
    Clear Trace File
    Drag And Drop On ${200,_200}

    ${actions}=             Create Dictionary
    ...                     272=press
    ...                     272=release
    Assert Pointer Button Events                    ${actions}

    ${movements}=    Evaluate
    ...    [(17, 14), (35,28), (53, 42), (71, 57), (89, 71), (107, 85), (125, 100), (143, 114), (160, 128), (178, 143), (196, 157), (200, 171), (200, 186), (200, 200)]
    Assert Pointer Movement Events                  ${movements}
