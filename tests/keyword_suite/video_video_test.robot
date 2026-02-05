*** Settings ***
Documentation       This suite tests VideoInput video related keywords.

Library             Process
Resource            kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::video
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Test Cases ***
Test Keyword Wait Still Screen Expect Timeout
    [Tags]                  yarf:certification_status: blocker
    [Setup]                 Start Video 20s
    Run Keyword And Expect Error
    ...                     *
    ...                     Wait Still Screen
    ...                     duration=20
    ...                     still_duration=5
    ...                     screenshot_interval=1

Test Keyword Wait Still Screen Expect Success
    [Tags]                  yarf:certification_status: blocker
    [Setup]                 Start Video 10s
    Wait Still Screen       duration=20             still_duration=5        screenshot_interval=1


*** Keywords ***
Start Video 20s
    [Documentation]    Starts the video.
    Start Process
    ...                     mkdir                   -p                      ${CURDIR}/videos

    Start Process
    ...                     ffmpeg
    ...                     -f
    ...                     lavfi
    ...                     -i
    ...                     testsrc\=duration\=20:size\=1280x720:rate\=30
    ...                     -c:v
    ...                     libx264
    ...                     ${CURDIR}/videos/test_video_20.mp4
    ...                     alias=CreateTestVideo1

    Wait For Process        CreateTestVideo1
    Start Process
    ...                     dbus-run-session
    ...                     --
    ...                     mpv
    ...                     --fs
    ...                     ${CURDIR}/videos/test_video_20.mp4

Start Video 10s
    [Documentation]    Starts the video.
    Start Process
    ...                     mkdir                   -p                      ${CURDIR}/videos

    Start Process
    ...                     ffmpeg
    ...                     -f
    ...                     lavfi
    ...                     -i
    ...                     testsrc\=duration\=10:size\=1280x720:rate\=30
    ...                     -c:v
    ...                     libx264
    ...                     ${CURDIR}/videos/test_video_10.mp4
    ...                     alias=CreateTestVideo2

    Wait For Process        CreateTestVideo2
    Start Process
    ...                     dbus-run-session
    ...                     --
    ...                     mpv
    ...                     --fs
    ...                     ${CURDIR}/videos/test_video_10.mp4
