*** Settings ***
Resource        kvm.resource

Task Tags
...    robot:stop-on-failure
...    yarf:category_id: com.canonical.yarf::vm
...    yarf:test_group_id: com.canonical.yarf::integration


*** Test Cases ***
Assert the guest boots Ubuntu
    [Documentation]    The word appears in the boot output long before a login
    ...    prompt, so it does not depend on how far cloud-init gets.
    [Tags]                  yarf:certification_status: blocker
    Match Text              Ubuntu                  timeout=600
