*** Settings ***
Documentation       Basic mode. Each test names where its expected value comes
...                 from in the GNOME Calculator 46.1 source.

Resource            calculator.resource

Suite Setup         Switch To Basic Mode


*** Test Cases ***
Operator Precedence
    [Documentation]    Multiplication goes before addition: 14, not 20.
    ...    Source: tests/test-equation.vala, "Order of operations".
    Calculate 2+3*4
    Entry Should Show 14
    Entry Should Not Show 20

Parentheses Override Precedence
    [Documentation]    Source: tests/test-equation.vala, "(1+2)×3 = 9".
    Calculate (2+3)*4
    Entry Should Show 20

Decimals Are Exact
    [Documentation]    It uses arbitrary precision, not binary floating point,
    ...    where 0.1 + 0.2 is 0.30000000000000004.
    ...    Source: tests/test-equation.vala, "1−0.9−0.1 = 0", lib/number.vala.
    Calculate 0.1+0.2
    Entry Should Show 0.3

Percentage Is Relative To The Left Operand
    [Documentation]    Source: tests/test-equation.vala, "Percentage".
    Calculate 100+1%
    Entry Should Show 101
    Calculate 100-20%
    Entry Should Show 80

Factorial
    [Documentation]    Source: tests/test-equation.vala, "5! = 120".
    Calculate 5!
    Entry Should Show 120

Irrational Result Has Nine Decimals
    [Documentation]    The square root of 2 is shown with nine decimals.
    ...    Source: tests/test-equation.vala, "2^0.5 = 1.414213562".
    Calculate 2^0.5
    Entry Should Show 1.414213562

Next Operation Continues From The Answer
    [Documentation]    An operator typed after a result applies to it. Only a
    ...    digit or the decimal point replaces a result, anything else is
    ...    added to it.
    ...    Source: lib/math-equation.vala, insert_text, "Clear result on next
    ...    digit entered".
    Calculate 6*7
    Entry Should Show 42
    Enter +8
    Entry Should Show 50

Division By Zero Shows An Error
    [Documentation]    Source: lib/number.vala, and the upstream scenario
    ...    tests/basic_mode.feature, "Division by zero".
    Calculate 5/0
    Entry Should Show Division by zero is undefined

Malformed Expression Shows An Error
    [Documentation]    An operator with nothing after it.
    ...    Source: lib/math-equation.vala, "Malformed expression".
    Calculate 7*
    Entry Should Show Malformed expression

Escape Clears The Entry
    [Documentation]    Source: src/math-display.vala, "Clear on escape".
    Calculate 123+456
    Entry Should Show 579
    Keys Combo              Escape
    Entry Should Not Show 579

Control Escape Clears The History
    [Documentation]    It clears the history, not the entry. It starts by
    ...    clearing the history, so there is only one row to read.
    ...    Source: src/math-window.vala, clear_cb.
    ...
    ...    No other test uses this equation: the history ignores an equation
    ...    that is the same as the last one, even after it was cleared.
    ...    Source: src/math-history.vala, insert_entry.
    Keys Combo              Control_L               Escape
    Calculate 321+123
    History Should Show 321+123
    Keys Combo              Control_L               Escape
    History Should Not Show 321+123
    Entry Should Show 444
