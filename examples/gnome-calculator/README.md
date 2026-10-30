# GNOME Calculator test suite

Functional tests of GNOME Calculator 46, the version in Ubuntu 24.04, running in
a QEMU virtual machine that YARF controls through VNC.

The functions under test were chosen by reading the calculator source, tag
`46.1`, at <https://gitlab.gnome.org/GNOME/gnome-calculator>. The expected values
come from the project's own tests (`tests/test-equation.vala`), and each test
says where in its documentation.

## Run it

Boot the Ubuntu 24.04 desktop ISO with a VNC server that listens on localhost
only. A USB tablet is needed for the pointer to land where it should.

```bash
qemu-system-x86_64 -enable-kvm -cpu host -smp 2 -m 2560 \
  -drive file=ubuntu-24.04.3-desktop-amd64.iso,media=cdrom,readonly=on \
  -boot d -vga std -device qemu-xhci -device usb-tablet \
  -display none -vnc 127.0.0.1:1
```

The suite was developed with 2560 MB of memory, which was enough. Ubuntu
recommends 4096 MB if you have it.

Choose _Try or Install Ubuntu_, wait for the desktop and close the installer
window. Then run the suite:

```bash
VNC_HOST=localhost VNC_PORT=1 yarf --platform Vnc examples/gnome-calculator
```

The suite opens the calculator from the Activities overview, so it needs the
calculator to be closed when it starts, and the overview to be closed too. It
quits the calculator when it ends.

## What is tested

| Test                                             | What it checks                                           | Source (GNOME Calculator 46.1)                    |
| ------------------------------------------------ | -------------------------------------------------------- | ------------------------------------------------- |
| Operator Precedence                              | `2+3*4` is 14, not 20                                    | `tests/test-equation.vala:409`                    |
| Parentheses Override Precedence                  | `(2+3)*4` is 20                                          | `tests/test-equation.vala:411`                    |
| Decimals Are Exact                               | `0.1+0.2` is 0.3, with no floating-point noise           | `tests/test-equation.vala:408`, `lib/number.vala` |
| Percentage Is Relative To The Left Operand       | `100+1%` is 101, `100-20%` is 80                         | `tests/test-equation.vala:421`, `:776`            |
| Factorial                                        | `5!` is 120                                              | `tests/test-equation.vala:434`                    |
| Irrational Result Has Nine Decimals              | `2^0.5` is 1.414213562                                   | `tests/test-equation.vala:487`                    |
| Next Operation Continues From The Answer         | `6*7` then `+8` is 50, as only a digit replaces a result | `lib/math-equation.vala:1448`                     |
| Division By Zero Shows An Error                  | `5/0` shows "Division by zero is undefined"              | `lib/number.vala:577`                             |
| Malformed Expression Shows An Error              | `7*` shows "Malformed expression"                        | `lib/math-equation.vala:1119`                     |
| Escape Clears The Entry                          | Escape empties the entry                                 | `src/math-display.vala:133`                       |
| Control Escape Clears The History                | Ctrl+Escape empties the history, and keeps the entry     | `src/math-window.vala:103`                        |
| Mode Shortcuts Switch Between Basic And Advanced | Ctrl+Alt+B and Ctrl+Alt+A                                | `src/gnome-calculator.vala:90`                    |
| Sine Uses Degrees By Default                     | `sin 30` is 0.5                                          | `tests/test-equation.vala:754`                    |
| Natural Logarithm Rounds Up To Nine Decimals     | `ln 2` is 0.693147181, the true value is 0.69314718056   | `tests/test-equation.vala:550`                    |
| Tangent Uses Degrees                             | `tan 10` is 0.176326981                                  | `tests/test-equation.vala:574`                    |

Not covered: Financial and Programming modes, unit and currency conversion,
variables and user functions, and preferences.

## How the checks work

The result of a calculation is shown in the entry, above the buttons. It also
stays in the history, and some buttons are labelled with digits. So the suite
never searches the whole screen. It reads a box next to the entry, placed
relative to the `mod` button, and compares whole lines of text:

- `Match Text` is not used to check a value. It accepts similar text and part of
  a line, so `12` matches `120` and `0.666666666` matches `0.666666667`. Every
  check in this suite was tried with a wrong value, and fails with it.
- The OCR doesn't read text in a very wide crop, or a lone digit. The boxes are
  about 340 pixels wide, and no test expects a one-character result.
- The OCR also drops repeated digits in a long number: it read `0.333333333` as
  `0333` and `0.666666667` as `0.66666667`, on a run where the same tests had
  passed before. So the tests only expect numbers without repeated digits.
- A check that something is _not_ shown also passes if the OCR reads nothing.
  Each one comes after a check that the text was shown.

A calculation that is the same as the last one in the history is not added to the
history again, even after the history was cleared (`src/math-history.vala`,
`insert_entry`). The test of the history uses an equation no other test uses.
