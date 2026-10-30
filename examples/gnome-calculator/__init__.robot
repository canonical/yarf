*** Settings ***
Documentation       Functional tests of GNOME Calculator 46, the version
...                 shipped in Ubuntu 24.04, running in a virtual machine
...                 that YARF controls through VNC.
...
...                 The functions to test and their expected results come
...                 from the calculator source, tag 46.1:
...                 https://gitlab.gnome.org/GNOME/gnome-calculator
Metadata            title    GNOME Calculator
Metadata            test_plan_id    com.canonical.yarf::example_gnome_calculator

Resource            calculator.resource

Suite Setup         Launch Calculator
Suite Teardown      Close Calculator

Test Tags
...                 yarf:category_id: com.canonical.yarf::example
...                 yarf:test_group_id: com.canonical.yarf::gnome_calculator
