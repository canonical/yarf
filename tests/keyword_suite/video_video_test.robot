*** Settings ***
Documentation       This suite tests VideoInput video related keywords.

Library             Process
Resource            kvm.resource

Suite Setup         Create Video Directory
Test Teardown       Terminate All Processes    kill=True

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::video
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Test Cases ***
Test Keyword Wait Still Screen Expect Timeout
    [Tags]                  yarf:certification_status: blocker
    [Setup]                 Start Video             30
    Wait For Video Playback

Test Keyword Wait Still Screen Expect Success
    [Tags]                  yarf:certification_status: blocker
    [Setup]                 Start Video             10
    Wait For Video Playback
    Wait Still Screen       duration=20             still_duration=5        screenshot_interval=1


*** Keywords ***
Create Video Directory
    [Documentation]    Creates the videos directory if it doesn't exist.
    Run Process
    ...                     mkdir                   -p                      ${CURDIR}/videos

Wait For Video Playback
    [Documentation]    Waits for the video player to render changing frames.
    Wait Until Keyword Succeeds                     15 seconds              1 second
    ...                     Run Keyword And Expect Error                    *
    ...                     Wait Still Screen       duration=3              still_duration=2        screenshot_interval=1

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
