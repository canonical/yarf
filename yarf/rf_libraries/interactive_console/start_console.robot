*** Settings ***
Documentation       Import all platform libraries and start an interactive mode

Library             String
Library             Interactive.py
Library             RobotDebug    repl=${True}


*** Variables ***
${PLATFORM_LIBRARIES}       None
${RESOURCES}                None


*** Test Cases ***
Import Platform Libraries
    @{libraries}=           Split String            ${PLATFORM_LIBRARIES}                           ,
    FOR    ${lib_path}    IN    @{libraries}
        Import Library          ${lib_path}
    END

Import Resources
    @{resources}=           Split String            ${RESOURCES}            ,
    FOR    ${res_path}    IN    @{resources}
        Import Resource         ${res_path}
    END

Robot Framework Debug REPL
    Log Interactive Mode Info
    Debug


*** Keywords ***
Log Interactive Mode Info
    Log To Console          ${\n}
    Log To Console          INFO: *** Welcome to the YARF interactive console. ***
    Log To Console          INFO: You can use this console to execute Robot Framework keywords interactively.
    Log To Console          INFO: The value of \$\{CURDIR} is CWD, you can change it using the `Set Variable` keyword.
    Log To Console          INFO: You can press RIGHT_ARROW to auto-complete the keyword.
    Log To Console          INFO: You can press CRTL + SPACE to view supported keywords on a prefix.
