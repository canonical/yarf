*** Settings ***
Documentation       Tests cursor detection on real screenshots using the YOLO model.
Resource            kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::image
...    yarf:test_group_id: com.canonical.yarf::video_input


*** Variables ***
${CONFIDENCE}       ${0.75}
${TOLERANCE}        ${15}


*** Test Cases ***
Test Cursor Detection On Dell BIOS Screenshot
    [Tags]                  yarf:certification_status: blocker
    Detect Cursor In Image
    ...                     ${CURDIR}/gui/mouse_dell_bios.jpg
    ...                     ${264}
    ...                     ${566}

Test Cursor Detection On HP BIOS Screenshot
    [Tags]                  yarf:certification_status: blocker
    Detect Cursor In Image
    ...                     ${CURDIR}/gui/mouse_hp_bios.png
    ...                     ${384}
    ...                     ${321}

Test Cursor Detection On Ubuntu Cropped Screenshot
    [Tags]                  yarf:certification_status: blocker
    Detect Cursor In Image
    ...                     ${CURDIR}/gui/mouse_ubuntu_cropped.jpg
    ...                     ${78}
    ...                     ${224}

Test Cursor Detection On Ubuntu Installer Screenshot
    [Tags]                  yarf:certification_status: blocker
    Detect Cursor In Image
    ...                     ${CURDIR}/gui/mouse_ubuntu_installer.png
    ...                     ${1305}
    ...                     ${797}

Test Text Cursor Detection On Calc
    [Tags]                  yarf:certification_status: blocker
    Detect Cursor In Image
    ...                     ${CURDIR}/gui/text_cursor_calc.jpg
    ...                     ${356}
    ...                     ${319}

Test Text Cursor Detection On Document
    [Tags]                  yarf:certification_status: blocker
    Detect Cursor In Image
    ...                     ${CURDIR}/gui/text_cursor_doc.jpg
    ...                     ${986}
    ...                     ${272}


Test Mouse Cursor Detection On App
    [Tags]                  yarf:certification_status: blocker
    Detect Cursor In Image
    ...                     ${CURDIR}/gui/hand_cursor_app.jpg
    ...                     ${635}
    ...                     ${673}


*** Keywords ***
Detect Cursor In Image
    [Arguments]             ${image_path}           ${expected_x}           ${expected_y}
    ${image}=               Evaluate
    ...                     PIL.Image.open(r"${image_path}")                modules=PIL.Image
    ${pos}=                 Find Cursor Position
    ...                     image=${image}
    ...                     confidence=${CONFIDENCE}
    Should Not Be Equal     ${pos}                  ${None}
    ...                     msg=Cursor not detected in ${image_path}
    ${x}=                   Set Variable            ${pos}[0]
    ${y}=                   Set Variable            ${pos}[1]
    Should Be True
    ...                     abs(${x} - ${expected_x}) <= ${TOLERANCE}
    ...                     msg=x=${x} not within ${TOLERANCE}px of expected ${expected_x}
    Should Be True
    ...                     abs(${y} - ${expected_y}) <= ${TOLERANCE}
    ...                     msg=y=${y} not within ${TOLERANCE}px of expected ${expected_y}
