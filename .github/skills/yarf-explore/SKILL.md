---
name: yarf-explore
description: Explore a graphical application on a virtual machine through the YARF MCP server, and write a YARF (Robot Framework) test suite for it. Use when asked to discover, explore or generate YARF tests for an application, for example "explore GNOME Calculator and write a YARF suite".
---

# Explore an application and write a YARF suite

You explore an application on a virtual machine, with the tools of the `yarf`
MCP server, and turn what works into a Robot Framework suite that runs on its
own with `yarf`. The full guide for people is
`docs/how-to/discover-a-test-suite-with-explore-mode.md`.

You are the one who decides what to try. The server gives you the screen, the
keyboard and the pointer, and records what you did.

## Before you start

1. Check that the server works: call `check_connection`. If the tool does not
   exist or it fails, stop and tell the user to follow the guide above (start the
   virtual machine, add the `yarf` server to your client). Do not try to work
   around it with other tools.
1. Get what you do not have, from the user. Ask for all of it in one message:
   - the application, and the **version that is on the machine**;
   - a link to its documentation, and to its repository, if there is one;
   - the VNC port of the machine (`VNC_PORT`, the port minus 5900);
   - where to write the suite (default `suites/<application>/`).
1. Say which machine state you expect, for example "a fresh desktop with the
   application closed". Ask the user to restore it if you cannot tell.

## Step 1: plan the scenarios, with evidence

Read the documentation and, if there is a repository, the source **at the
version that is on the machine** (check out its tag in a temporary folder
outside the YARF checkout, not `main`). Prefer the project's own tests and
specification as the source of expected values.

Write `<suite>/plan.md`, one row per scenario:

| Feature | Scenario | Expected result | Evidence | Needs a fresh start |
| ------- | -------- | --------------- | -------- | ------------------- |

- Every expected result cites its evidence: a file and line, or a link. With no
  evidence, write `TO CHECK` and do **not** turn it into a test. Never fill a
  gap with general knowledge.
- Cover what a person can do: by mouse and by keyboard, every mode and panel
  and back, and the settings.
- Show the plan to the user and wait for their answer, unless they asked you to
  run without stopping.

## Step 2: explore

Run each scenario with the tools of the server, one action at a time.

- Call `screenshot` before and after every action, and look at it.
- Target text that appears **once** on the screen. The text is matched
  approximately and anywhere, so a `7` matches the `7` in the clock. If a text is
  not unique, or the OCR does not read it (symbols such as `×`, `=` and `−` are
  often misread), use `save_template` and target the image.
- Check each result with `match_text` or `match_template`. These accept similar
  text, so `12` also matches `120`. They show that something is on the screen,
  not that a value is exact (see step 4).
- After an action that moves something, wait before the next one: add a `Sleep`
  with `run_keyword`. The export runs the steps back to back, without the time
  you took.
- Use short, separate scenarios, and call `get_history` to retrace your steps.
- An application can remember its state between runs (its mode, a setting), and
  can ignore an action that repeats. Note it in the plan when you see it.
- If the server refuses a keyword, do not look for a way around it. Say so in
  the report.

When a result is not what the evidence says, do not change the expectation to
fit. That is a finding: record it and continue.

## Step 3: export

Call `export_suite` once per scenario, with `event_ids` to take only the steps
of that scenario. Give each template a unique name. The result says where the
files were written: copy them into `<suite>/`, so that each `.robot` file sits
next to a shared `templates/` folder.

## Step 4: make the suite trustworthy

Open every exported file and edit it.

1. Add `[Documentation]` to each test: what it checks, and its evidence.
1. Add a suite setup that opens the application from a known state, and a
   teardown that closes it. The export holds the steps you took, not the state
   you started from.
1. Replace each approximate check of a **value** by an exact one. Read the
   region where the value is shown, and compare whole lines. The example
   `examples/gnome-calculator/calculator.resource` does it with
   `Get Lines Of`, `Area Should Contain` and `Area Should Not Contain`: copy and
   adapt it. Anchor the region to a text that is always there, not to
   coordinates.
1. Prove each check can fail: run the test once with a close but wrong value
   (`101` for `100`, a last digit off by one) and see it fail. Put the right
   value back.
1. Keep out what you cannot check, and say why in the report.

## Step 5: run it, and make it stable

Run the suite on the machine, from the YARF checkout:

```bash
VNC_HOST=localhost VNC_PORT=<port> uv run yarf --platform Vnc <suite>
```

Start every run from the same fresh state (ask the user to restore the machine
between runs). Run it **three times in a row** and see it pass.

When a test fails, find out why before you touch it: a real problem of the
application, a wrong expectation, an OCR misread, or a timing problem. Fix the
test, never loosen a check to make it pass. A test that is still flaky after
three attempts leaves the suite, and goes in the report.

## Step 6: report

End with a short summary:

- scenarios planned, tests written, how many runs in a row passed;
- tests left out, and why (flaky, `TO CHECK`, not observable);
- problems of the application found, with their evidence;
- what the OCR could not read, and what you did about it;
- what a person still has to do, for example tighten a check by hand.

## Limits of this version

- You cannot start, snapshot or restore the machine: the user does.
- The server only runs GUI keywords. It does not give you the host, and it
  should not.
- Say clearly what you did not cover, instead of implying the suite is complete.
