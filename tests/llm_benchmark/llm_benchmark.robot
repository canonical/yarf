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
...
...                 The VM must be QEMU, started like in
...                 .github/scripts/llm-benchmark/start-vm.sh with a monitor
...                 socket at ${QEMU_MONITOR}: every test starts from a VM
...                 snapshot of the prepared desktop.
Library             Collections
Library             OperatingSystem
Library             yarf.rf_libraries.libraries.llm_client.LlmClient
Library             vm_snapshot.py          ${QEMU_MONITOR}
Resource            kvm.resource

Suite Setup         Prepare Desktop
Test Setup          Benchmark Setup
Test Teardown       Record Llm Usage


*** Variables ***
${PROVIDER}             openrouter
${MODEL}                qwen/qwen3.5-9b
${ENDPOINT}             /chat/completions
${IMAGE_FORMAT}         WEBP
${USAGE_FILE}           ${OUTPUT_DIR}/usage.jsonl
${FIREFOX_POLICIES}     ${CURDIR}/firefox_policies.json
${QEMU_MONITOR}         /tmp/yarf-vm-monitor.sock
${PROMPT}               ubuntu@ubuntu


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
Benchmark Setup
    Restore Vm Snapshot
    Configure Llm Client    provider=${PROVIDER}    model=${MODEL}
    ...                     endpoint=${ENDPOINT}    image_format=${IMAGE_FORMAT}
    ...                     collect_usage=True

Prepare Desktop
    [Documentation]    Wait for the live session to boot, close its
    ...    installer, turn off screen blanking and do the slow first Firefox
    ...    start without its first-run wizard, so that the tests measure
    ...    the model. Then save a VM snapshot, which every test restores. The
    ...    ready desktop is saved to ${OUTPUT_DIR}/desktop-ready.png.
    Wait For Live Session And Close Installer
    # See firefox_policies.json for why each policy is needed.
    ${policies}=            Evaluate
    ...                     shlex.quote(json.dumps({"policies": json.loads(pathlib.Path($FIREFOX_POLICIES).read_text())["policies"]}))
    ...                     modules=json,pathlib,shlex
    # Without idle-delay 0, the screen blanks during long model runs.
    ${command}=             Catenate                SEPARATOR=${SPACE}&&${SPACE}
    ...                     gsettings set org.gnome.desktop.session idle-delay 0
    ...                     sudo mkdir -p /etc/firefox/policies
    ...                     echo ${policies} | sudo tee /etc/firefox/policies/policies.json > /dev/null
    Run In Terminal         ${command}
    # Start Firefox once, so that the snapshot has its profile and snap set
    # up and the tests do not pay for the slow first start. Headless, as a
    # window would hide the terminal; --screenshot makes it exit once loaded.
    Run In Terminal
    ...                     firefox --headless --screenshot /tmp/warmup.png about:blank
    ...                     timeout=300
    ${screenshot}=          Grab Screenshot
    Evaluate                $screenshot.save($OUTPUT_DIR + "/desktop-ready.png")
    Save Vm Snapshot

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
    [Documentation]    Run a command in a new terminal, which closes once
    ...    the command succeeds. Fail if it is still open after ${timeout} s.
    [Arguments]             ${command}              ${timeout}=60
    # Hid starts at (0, 0), which triggers the GNOME Activities hot corner.
    Hid.Move Pointer To Proportional                0.5                     0.5
    Keys Combo              Control_L               Alt_L                   t
    Match Text              ${PROMPT}               timeout=60
    Type String             (${command}) && exit
    Keys Combo              Return
    Wait Until Keyword Succeeds                     ${timeout} s            2 s
    ...                     Ensure ${PROMPT} Does Not Match                 timeout=1

Record Llm Usage
    ${usage}=               Get Llm Usage
    Set To Dictionary       ${usage}                test=${TEST_NAME}       status=${TEST_STATUS}
    ${line}=                Evaluate                json.dumps($usage)      modules=json
    Append To File          ${USAGE_FILE}           ${line}\n
