*** Settings ***
Documentation       Advanced mode. Each test names where its expected value
...                 comes from in the GNOME Calculator 46.1 source.

Resource            calculator.resource

Suite Setup         Switch To Advanced Mode


*** Test Cases ***
Mode Shortcuts Switch Between Basic And Advanced
    [Documentation]    Source: src/gnome-calculator.vala, Ctrl+Alt+B and A.
    Switch To Basic Mode
    Switch To Advanced Mode
    Match Text              Angle                   timeout=5

Sine Uses Degrees By Default
    [Documentation]    sin 30 is exactly 0.5 when the angle is in degrees.
    ...    Source: tests/test-equation.vala, "sin 30 ^ 4 = 0.0625".
    Calculate sin 30
    Entry Should Show 0.5

Natural Logarithm Rounds Up To Nine Decimals
    [Documentation]    ln 2 is 0.69314718056, so the ninth decimal goes up.
    ...    Source: tests/test-equation.vala, "ln 2 = 0.693147181".
    Calculate ln 2
    Entry Should Show 0.693147181

Tangent Uses Degrees
    [Documentation]    Source: tests/test-equation.vala, "tan 10 = 0.176326981".
    Calculate tan 10
    Entry Should Show 0.176326981
