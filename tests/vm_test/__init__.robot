*** Settings ***
Documentation       This suite boots an Ubuntu cloud image in QEMU and checks
...                 that the guest reaches userspace, exercising the Vnc
...                 platform against a real VM rather than a compositor.
Metadata            title    VM Suite
Metadata            test_plan_id    com.canonical.yarf::vm_test
