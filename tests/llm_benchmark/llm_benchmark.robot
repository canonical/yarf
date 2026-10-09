*** Settings ***
Documentation       Benchmark of LLM-driven GUI navigation on an Ubuntu 24.04
...                 desktop live session over VNC. The token usage, inference
...                 time and cost of every test are appended to ${USAGE_FILE}.
...
...                 Run locally against a VM with a VNC display, with --debug
...                 like in CI so that the logs show the model's screenshots:
...                 VNC_PORT=0 yarf --debug --platform Vnc tests/llm_benchmark --
...                 --variable PROVIDER:openrouter
...                 --variable MODEL:qwen/qwen3.5-9b
Library             Collections
Library             OperatingSystem
Library             yarf.rf_libraries.libraries.llm_client.LlmClient
Resource            kvm.resource

Suite Setup         Prepare Desktop
Test Setup          Configure Llm Client    provider=${PROVIDER}    model=${MODEL}
...                     endpoint=${ENDPOINT}    image_format=${IMAGE_FORMAT}
...                     collect_usage=True
Test Teardown       Benchmark Teardown


*** Variables ***
${PROVIDER}             openrouter
${MODEL}                qwen/qwen3.5-9b
${ENDPOINT}             /chat/completions
${IMAGE_FORMAT}         WEBP
${USAGE_FILE}           ${OUTPUT_DIR}/usage.jsonl
${FIREFOX_POLICIES}     {"policies": {"OverrideFirstRunPage": "", "OverridePostUpdatePage": "", "DontCheckDefaultBrowser": true, "DisableTelemetry": true, "UserMessaging": {"SkipOnboarding": true, "ExtensionRecommendations": false, "FeatureRecommendations": false, "MoreFromMozilla": false}, "Preferences": {"browser.sessionstore.resume_from_crash": {"Value": false, "Status": "locked"}}}}
# Closes the apps used by the tests and reverts the files they create.
${RESET_SCRIPT}         SEPARATOR=
...                     pkill -u $USER -f 'gnome-text-editor|gnome-calculator|gnome-control-center
...                     |soffice|rhythmbox|thunderbird|snap-store|yelp|totem|eog|evince
...                     |ubuntu-desktop-bootstrap|gnome-system-monitor|baobab|gnome-disks
...                     |gnome-logs|gnome-characters|seahorse|shotwell|transmission
...                     |remmina|simple-scan|software-properties|update-manager
...                     |aisleriot|gnome-mahjongg|gnome-mines|gnome-sudoku|snapshot|loupe
...                     |gnome-clocks|gnome-weather|gnome-calendar|gnome-maps|gnome-contacts
...                     |gnome-power-statistics|gnome-font-viewer|deja-dup|usb-creator
...                     |apport-gtk|firmware-updater|desktop-security-center
...                     |system-config-printer|nm-connection-editor|language-selector';
...                     ${SPACE}pkill -x firefox;
...                     ${SPACE}pkill -x nautilus; sleep 3;
...                     ${SPACE}rm -rf ~/Music/classical ~/.local/share/Trash/files/*
...                     ${SPACE}~/.local/share/Trash/info/*
...                     ${SPACE}~/.local/share/org.gnome.TextEditor
...                     ${SPACE}~/snap/firefox/common/.mozilla/firefox/*/cookies.sqlite*
...                     ${SPACE}~/snap/firefox/common/.mozilla/firefox/*/sessionstore*;
...                     ${SPACE}grep -rlZ --exclude-dir='.*' --exclude-dir=snap
...                     ${SPACE}--exclude=yarf_reset.sh 'hello from YARF' ~
...                     ${SPACE}| xargs -0r rm -f;
...                     ${SPACE}gsettings reset org.gnome.Settings last-panel;
...                     ${SPACE}gsettings set org.gnome.desktop.session idle-delay 0;
...                     ${SPACE}pkill -u $USER -f gnome-terminal


*** Test Cases ***
Open Settings Network Panel
    Multiple Step Action
    ...                     Open the Settings application and show the Network panel
    ...                     max_steps=12
    Assert State            the Settings application is open on the Network panel

Create And Save Text Editor Note
    ${task}=                Catenate                SEPARATOR=${SPACE}
    ...                     Open the text editor, create a new note,
    ...                     type "hello from YARF", and save it
    Multiple Step Action    ${task}                 max_steps=20
    ${state}=               Catenate                SEPARATOR=${SPACE}
    ...                     a saved text editor note containing "hello from YARF"
    ...                     is visible
    Assert State            ${state}

Create And Trash Music Folder
    Multiple Step Action    task=Open the File explorer in the dock and create new folder under music called "classical"
    Assert State            The folder "classical" is created under music in nautilus
    Multiple Step Action    task=Send the "classical" folder to the trash
    Assert State            The folder "classical" no longer present
    Multiple Step Action    task=Close the file explorer
    Assert State            nautilus is closed

Calculate With Calculator
    Multiple Step Action    task=Open the calculator, add "1" and "3", and square it
    Assert State            The calculator is open and it shows 16
    Multiple Step Action    task=Close the calculator
    Assert State            The calculator is closed

Play YouTube Video In Firefox
    Multiple Step Action    task=Open firefox, navigate to youtube, search for "introducing ubuntu resolute racoon" and play the video
    Assert State            Firefox is open, youtube is loaded, and a the ubuntu video is playing
    Multiple Step Action    task=Close firefox
    Assert State            Firefox is closed

Open Canonical Release Notes
    Multiple Step Action    task=Open firefox, navigate to canonical.com, search for "Ubuntu 26.04 LTS release notes" and open the press release
    Assert State            Firefox is open, and the 26.04 LTS release notes documentation page is open
    Multiple Step Action    task=Close firefox
    Assert State            Firefox is closed


*** Keywords ***
Benchmark Teardown
    Record Llm Usage
    Run Keyword And Ignore Error
    ...                     Run In Terminal         bash ~/yarf_reset.sh; exit

Prepare Desktop
    [Documentation]    Wait for the live session to boot, close its
    ...    installer, install the reset script and do the slow (~40 s) first
    ...    Firefox start without its first-run wizard, so that the tests measure
    ...    the model. The ready desktop is saved to
    ...    ${OUTPUT_DIR}/desktop-ready.png.
    Wait For Live Session And Close Installer
    Run In Terminal         echo "${RESET_SCRIPT}" > ~/yarf_reset.sh; bash ~/yarf_reset.sh; exit
    Run In Terminal
    ...                     sudo mkdir -p /etc/firefox/policies && echo '${FIREFOX_POLICIES}' | sudo tee /etc/firefox/policies/policies.json > /dev/null; firefox about:blank & sleep 60; pkill -x firefox; sleep 5; exit
    Sleep                   65s
    ${screenshot}=          Grab Screenshot
    Evaluate                $screenshot.save($OUTPUT_DIR + "/desktop-ready.png")

Wait For Live Session And Close Installer
    [Documentation]    The live session boots (~2 min) to the installer's
    ...    language page. Wait for it, then close the installer.
    # Hid starts at (0, 0), which triggers the GNOME Activities hot corner.
    Hid.Move Pointer To Proportional                0.5                     0.5
    Wait Until Keyword Succeeds                     10 min                  10 s
    ...                     Installer Is Shown
    # The installer has the keyboard focus, so a terminal cannot be opened.
    Keys Combo              Alt_L                   F4
    # The window fades out, so retry until its text is gone.
    Wait Until Keyword Succeeds                     30 s                    3 s
    ...                     Ensure Choose your language Does Not Match      timeout=1

Installer Is Shown
    [Documentation]    Check for the installer's language page, leaving the
    ...    Activities overview first, as it hides the window contents.
    ${overview}=            Run Keyword And Return Status
    ...                     Match Text              Type to search          timeout=1
    IF    ${overview}    Keys Combo    Escape
    Match Text              Choose your language    timeout=5

Run In Terminal
    [Arguments]             ${command}
    # Hid starts at (0, 0), which triggers the GNOME Activities hot corner.
    Hid.Move Pointer To Proportional                0.5                     0.5
    Keys Combo              Control_L               Alt_L                   t
    Sleep                   8s
    Type String             ${command}
    Keys Combo              Return
    Sleep                   6s

Record Llm Usage
    ${usage}=               Get Llm Usage
    Set To Dictionary       ${usage}                test=${TEST_NAME}       status=${TEST_STATUS}
    ${line}=                Evaluate                json.dumps($usage)      modules=json
    Append To File          ${USAGE_FILE}           ${line}\n
