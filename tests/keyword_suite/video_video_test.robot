*** Settings ***
Documentation       This suite tests VideoInput video related keywords.

Library             Process
Resource            kvm.resource

Suite Setup         Create Video Directory

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::video
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Test Cases ***
Test Keyword Wait Still Screen Expect Timeout
    [Tags]                  yarf:certification_status: blocker
    [Setup]                 Start Video             20
    Run Keyword And Expect Error
    ...                     *
    ...                     Wait Still Screen
    ...                     duration=20
    ...                     still_duration=5
    ...                     screenshot_interval=1

Test Keyword Wait Still Screen Expect Success
    [Tags]                  yarf:certification_status: blocker
    [Setup]                 Start Video             10
    Wait Still Screen       duration=20             still_duration=5        screenshot_interval=1


*** Keywords ***
Create Video Directory
    [Documentation]    Creates the videos directory if it doesn't exist.
    Run Process
    ...                     mkdir                   -p                      ${CURDIR}/videos

Start Video
    [Documentation]    Generate and start a video with given duration (seconds).
    [Arguments]             ${duration}
    Start Process
    ...                     ffmpeg
    ...                     -f
    ...                     lavfi
    ...                     -i
    ...                     testsrc\=duration\=${duration}:size\=1280x720:rate\=30
    ...                     -c:v
    ...                     libx264
    ...                     ${CURDIR}/videos/test_video_${duration}.mp4
    ...                     alias=CreateTestVideo

    Wait For Process        CreateTestVideo
    Start Process
    ...                     dbus-run-session
    ...                     --
    ...                     mpv
    ...                     --fs
    ...                     ${CURDIR}/videos/test_video_${duration}.mp4
