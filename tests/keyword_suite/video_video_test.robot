*** Settings ***
Documentation       This suite tests VideoInput video related keywords.

Resource            kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::video
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Test Cases ***
Test Keyword Wait Still Screen Expect Timeout
    [Tags]                  yarf:certification_status: blocker
    Run Keyword And Expect Error
    ...                     *
    ...                     Wait Still Screen
    ...                     duration=20
    ...                     still_duration=5
    ...                     screenshot_interval=1

Test Keyword Wait Still Screen Expect Success
    [Tags]                  yarf:certification_status: blocker
    Wait Still Screen       duration=20             still_duration=5        screenshot_interval=1
