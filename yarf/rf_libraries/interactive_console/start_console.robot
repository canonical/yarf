*** Settings ***
Documentation       Import all platform libraries and start an interactive mode

Library             String
Library             RobotDebug    repl=${True}


*** Variables ***
${PLATFORM_LIBRARIES}       None
${RESOURCES}                None
${CURDIR}                   ${EXECDIR}


*** Test Cases ***
Log CURDIR Info
    Log To Console          INFO:The value of CURDIR is: ${CURDIR}
    Log To Console          INFO:You can change the value of CURDIR by using \$\{CURDIR\}\= <path-you-want>\n

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
    Debug
